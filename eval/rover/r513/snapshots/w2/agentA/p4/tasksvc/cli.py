# -*- coding: utf-8 -*-
"""任务队列 CLI 服务（Python 3 标准库，无第三方依赖）。

运行方式（包位于工作区根目录）：
    python3 -B -m tasksvc.cli --db <path> [--now <epoch秒>] <子命令> [参数...]

全局选项 --db/--now 必须写在子命令之前。

子命令：
    add <text> [--ttl <秒>]   -> {"task": {...}}
    list [--status open|done|expired|all]   -> {"tasks": [...]}   缺省 open
    done <id>                 -> {"task": {...}}   幂等
    stats                     -> {"total","open","done","expired"}
    expire                    -> {"expired":[id, ...]}   真删除已过期任务

退出码：
    0 成功；2 参数/用法错；3 未知 id；4 存储损坏。
每条命令向 stdout 打印恰好一个 JSON 对象（ensure_ascii=False + 尾换行）。

自检：
    python3 -B -m tasksvc.cli --selftest
    PASS -> 退出码 0；FAIL -> 非 0。

统计口径：total = 现存任务数（真删除后不计）；open/done/expired 反映当前时刻视图，
实现上三者互斥 —— 过期优先于 done，故 total 可能大于 open+done+expired。
"""

import json
import os
import sys
import tempfile
import time

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


# --------------------------------------------------------------------------
# JSON 输出（唯一输出通道，约束：恰好一个 JSON 对象）
# --------------------------------------------------------------------------
def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def fail(code, token):
    emit({"error": token})
    return code


class BadRequest(Exception):
    """参数/用法错误 -> 退出码 2。"""


# --------------------------------------------------------------------------
# 原子存储层
# --------------------------------------------------------------------------
class StoreError(Exception):
    """存储文件损坏（非 JSON 或 schema 不符）-> 退出码 4。"""


def _validate(raw):
    if not isinstance(raw, dict):
        raise StoreError("root not object")
    if "next_id" not in raw or not isinstance(raw["next_id"], int) or isinstance(raw["next_id"], bool):
        raise StoreError("bad next_id")
    if raw["next_id"] < 1:
        raise StoreError("bad next_id")
    tasks = raw.get("tasks", [])
    if not isinstance(tasks, list):
        raise StoreError("bad tasks")
    for t in tasks:
        if not isinstance(t, dict):
            raise StoreError("bad task")
        if not isinstance(t.get("id"), int) or isinstance(t.get("id"), bool):
            raise StoreError("bad task id")
        if not isinstance(t.get("text"), str):
            raise StoreError("bad task text")
        if not isinstance(t.get("done"), bool):
            raise StoreError("bad task done")
        if not isinstance(t.get("created_at"), (int, float)):
            raise StoreError("bad task created_at")
        exp = t.get("expires_at")
        if exp is not None and not isinstance(exp, (int, float)):
            raise StoreError("bad task expires_at")
    return raw


def load(db_path):
    if not os.path.exists(db_path):
        return {"next_id": 1, "tasks": []}
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (ValueError, OSError) as exc:
        raise StoreError(str(exc))
    return _validate(raw)


def save(db_path, data):
    """写临时文件 + 同目录原子重命名；不残留临时文件。"""
    directory = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, db_path)  # 原子
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# --------------------------------------------------------------------------
# 领域逻辑
# --------------------------------------------------------------------------
def is_expired(task, now):
    """now >= expires_at 即为已过期；无 expires_at 永不过期。"""
    exp = task.get("expires_at")
    return exp is not None and now >= exp


def build_view(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


def is_open(task, now):
    return (not task["done"]) and (not is_expired(task, now))


def cmd_add(data, now, text, ttl):
    if ttl is not None and ttl <= 0:
        raise BadRequest()
    if text.strip() == "":
        raise BadRequest()
    task = {
        "id": data["next_id"],
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": (float(now) + float(ttl)) if ttl is not None else None,
    }
    data["next_id"] += 1  # 只增不减，删除/过期不复用
    data["tasks"].append(task)
    return {"task": build_view(task)}


def cmd_list(data, now, status):
    if status not in ("open", "done", "expired", "all"):
        raise BadRequest()

    def match(t):
        exp = is_expired(t, now)
        if status == "open":
            return (not t["done"]) and (not exp)
        if status == "done":
            return t["done"] and (not exp)  # 过期优先于 done（互斥）
        if status == "expired":
            return exp
        return True  # all

    ts = [t for t in data["tasks"] if match(t)]
    ts.sort(key=lambda t: t["id"])
    return {"tasks": [build_view(t) for t in ts]}


def cmd_done(data, now, tid):
    for t in data["tasks"]:
        if t["id"] == tid:
            t["done"] = True  # 幂等：已是 done 仍成功
            return {"task": build_view(t)}
    raise KeyError(tid)


def cmd_stats(data, now):
    """三视图互斥统计；三者之和 <= total（total 含已被 done 的过期任务）。"""
    total = len(data["tasks"])
    open_ = sum(1 for t in data["tasks"] if is_open(t, now))
    expired = sum(1 for t in data["tasks"] if is_expired(t, now))
    done = sum(1 for t in data["tasks"] if (not is_expired(t, now)) and t["done"])
    return {"total": total, "open": open_, "done": done, "expired": expired}


def cmd_expire(data, now):
    expired_ids = sorted(t["id"] for t in data["tasks"] if is_expired(t, now))
    data["tasks"] = [t for t in data["tasks"] if not is_expired(t, now)]  # 真删除
    return {"expired": expired_ids}


# --------------------------------------------------------------------------
# 参数解析（全局选项在子命令之前）
# --------------------------------------------------------------------------
def parse_global(argv):
    db_path = None
    now = None
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--db":
            if i + 1 >= len(argv):
                raise BadRequest()
            db_path = argv[i + 1]
            i += 2
        elif tok == "--now":
            if i + 1 >= len(argv):
                raise BadRequest()
            try:
                now = float(argv[i + 1])
            except ValueError:
                raise BadRequest()
            i += 2
        else:
            break
    if db_path is None:
        raise BadRequest()
    if now is None:
        now = time.time()  # 回落系统时钟，不报错
    return db_path, now, argv[i:]


def parse_int(token):
    try:
        return int(token)
    except (TypeError, ValueError):
        raise BadRequest()


def run(argv, stdout=sys.stdout):
    """执行一条命令，返回退出码；stdout 可注入（自检用）。"""
    saved = sys.stdout
    sys.stdout = stdout
    try:
        db_path, now, rest = parse_global(argv)

        if not rest:
            raise BadRequest()
        sub = rest[0]
        args = rest[1:]

        data = load(db_path)

        if sub == "add":
            if not args:
                raise BadRequest()
            text = args[0]
            ttl = None
            j = 1
            while j < len(args):
                if args[j] == "--ttl":
                    if j + 1 >= len(args):
                        raise BadRequest()
                    ttl = parse_int(args[j + 1])
                    j += 2
                else:
                    raise BadRequest()
            result = cmd_add(data, now, text, ttl)
            save(db_path, data)
        elif sub == "list":
            status = "open"
            j = 0
            while j < len(args):
                if args[j] == "--status":
                    if j + 1 >= len(args):
                        raise BadRequest()
                    status = args[j + 1]
                    j += 2
                else:
                    raise BadRequest()
            if status not in ("open", "done", "expired", "all"):
                raise BadRequest()
            result = cmd_list(data, now, status)
        elif sub == "done":
            if not args:
                raise BadRequest()
            tid = parse_int(args[0])
            try:
                result = cmd_done(data, now, tid)
            except KeyError:
                return fail(EXIT_NOT_FOUND, "not_found")
            save(db_path, data)
        elif sub == "stats":
            if args:
                raise BadRequest()
            result = cmd_stats(data, now)
        elif sub == "expire":
            if args:
                raise BadRequest()
            result = cmd_expire(data, now)
            save(db_path, data)
        else:
            raise BadRequest()

        emit(result)
        return EXIT_OK
    except BadRequest:
        return fail(EXIT_BAD_REQUEST, "bad_request")
    except StoreError:
        return fail(EXIT_BAD_STORE, "bad_store")
    finally:
        sys.stdout = saved


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def _call(argv, db_path):
    import io
    buf = io.StringIO()
    code = run(argv, stdout=buf)
    out = buf.getvalue()
    parsed = None
    stripped = out.strip("\n")
    if stripped != "":
        parsed = json.loads(stripped)  # 必须恰好一个 JSON 对象
    return code, parsed, out


def selftest(tmp):
    ok = True
    db = os.path.join(tmp, "db.json")

    def chk(name, cond, extra=""):
        nonlocal ok
        if cond:
            print("PASS %s" % name)
        else:
            ok = False
            print("FAIL %s %s" % (name, extra))

    # 1. add + text 逐字节保留（中文/emoji/首尾空格）
    txt = "  hello 世界 🚀  "
    code, out, raw = _call(["--db", db, "--now", "1000", "add", txt, "--ttl", "10"], db)
    chk("add.ok", code == 0, code)
    chk("add.text_roundtrip", out["task"]["text"] == txt, out["task"]["text"])
    chk("add.expires_at", out["task"]["expires_at"] == 1010.0, out["task"]["expires_at"])
    chk("add.created_at", out["task"]["created_at"] == 1000.0)
    chk("add.id", out["task"]["id"] == 1)

    # 2. next_id 持久化
    with open(db, "r", encoding="utf-8") as f:
        raw_db = json.load(f)
    chk("persist.next_id", raw_db["next_id"] == 2, raw_db["next_id"])

    # 3. 空白 text -> bad_request
    code, out, _ = _call(["--db", db, "--now", "1000", "add", "   "], db)
    chk("add.blank_bad", code == 2 and out == {"error": "bad_request"}, (code, out))

    # 4. ttl <= 0 -> bad_request
    code, out, _ = _call(["--db", db, "--now", "1000", "add", "x", "--ttl", "0"], db)
    chk("add.ttl_nonpos", code == 2 and out == {"error": "bad_request"}, (code, out))

    # 5. 未知子命令
    code, out, _ = _call(["--db", db, "--now", "1000", "bogus"], db)
    chk("unknown_sub", code == 2 and out == {"error": "bad_request"}, (code, out))

    # 6. 状态视图：过期优先于 done（互斥）
    _call(["--db", db, "--now", "1000", "add", "second"], db)
    code, out, _ = _call(["--db", db, "--now", "1005", "done", "1"], db)
    chk("done.ok", code == 0 and out["task"]["done"] is True, (code, out))
    code, out, _ = _call(["--db", db, "--now", "1011", "list", "--status", "expired"], db)
    chk("expired_over_done", [t["id"] for t in out["tasks"]] == [1], out)
    code, out, _ = _call(["--db", db, "--now", "1011", "list", "--status", "done"], db)
    chk("expired_not_done", out["tasks"] == [], out)

    # 7. done 幂等
    code, out, _ = _call(["--db", db, "--now", "1005", "done", "2"], db)
    chk("done.first", code == 0)
    code, out, _ = _call(["--db", db, "--now", "1005", "done", "2"], db)
    chk("done.idempotent", code == 0 and out["task"]["done"] is True, (code, out))

    # 8. 未知 id -> not_found / 3
    code, out, _ = _call(["--db", db, "--now", "1000", "done", "999"], db)
    chk("done.not_found", code == 3 and out == {"error": "not_found"}, (code, out))

    # 9. 非整数 id -> bad_request / 2
    code, out, _ = _call(["--db", db, "--now", "1000", "done", "abc"], db)
    chk("done.bad_id", code == 2 and out == {"error": "bad_request"}, (code, out))

    # 10. stats：三视图互斥（task1 已 done 且已过期 -> 只计 expired）
    code, out, _ = _call(["--db", db, "--now", "1011", "stats"], db)
    chk("stats", out == {"total": 2, "open": 0, "done": 1, "expired": 1}, out)

    # 11. expire 真删除
    code, out, _ = _call(["--db", db, "--now", "1011", "expire"], db)
    chk("expire.ids", out["expired"] == [1], out)
    code, out, _ = _call(["--db", db, "--now", "1011", "list", "--status", "all"], db)
    chk("expire.deleted", [t["id"] for t in out["tasks"]] == [2], out)

    # 12. id 永不复用（next_id 只增）
    code, out, _ = _call(["--db", db, "--now", "1011", "add", "third"], db)
    chk("id.monotonic", out["task"]["id"] == 3, out["task"]["id"])

    # 13. list 按 id 升序
    code, out, _ = _call(["--db", db, "--now", "1011", "list", "--status", "all"], db)
    ids = [t["id"] for t in out["tasks"]]
    chk("list.sorted", ids == sorted(ids) and ids == [2, 3], ids)

    # 14. 损坏存储 -> bad_store / 4
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{ not json")
    code, out, _ = _call(["--db", bad, "--now", "1", "list"], bad)
    chk("store.invalid_json", code == 4 and out == {"error": "bad_store"}, (code, out))
    bad2 = os.path.join(tmp, "bad2.json")
    with open(bad2, "w", encoding="utf-8") as f:
        json.dump({"nope": 1}, f)
    code, out, _ = _call(["--db", bad2, "--now", "1", "list"], bad2)
    chk("store.bad_schema", code == 4 and out == {"error": "bad_store"}, (code, out))

    # 15. 原子写：不残留临时文件
    leftovers = [n for n in os.listdir(tmp) if n.startswith(".tasksvc-")]
    chk("atomic.no_temp_leftover", leftovers == [], leftovers)

    # 16. 未给 --now 回落系统时钟、不报错
    db2 = os.path.join(tmp, "nowfall.json")
    code, out, raw = _call(["--db", db2, "add", "clock"], db2)
    chk("now.fallback", code == 0 and out["task"]["created_at"] <= time.time(), (code, out))
    chk("output.single_json", raw.count("\n") == 1 and raw.endswith("\n"), repr(raw))

    if ok:
        print("PASS tasksvc selftest")
        return 0
    print("FAIL tasksvc selftest")
    return 1


def main(argv):
    if argv and argv[0] == "--selftest":
        import tempfile as _tempfile
        with _tempfile.TemporaryDirectory() as tmp:
            return selftest(tmp)
    return run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
