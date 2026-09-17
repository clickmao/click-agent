"""tasksvc CLI 入口。

运行:
    python3 -B -m tasksvc.cli --db <path> [--now <epoch>] <command> [args]

全局选项 --db / --now 写在子命令之前。
每条命令结束向 stdout 打印恰好一个 JSON 对象 (ensure_ascii=False, 带一个尾换行),
不打印其它内容。

子命令:
    add <text> [--ttl <秒>]            -> {"task": {...}}
    list [--status open|done|expired|all] -> {"tasks": [...]}  缺省 open
    done <id>                          -> {"task": {...}}
    stats                              -> {"total","open","done","expired"}
    expire                             -> {"expired":[<id>, ...]}

退出码:
    0 成功; 2 bad_request; 3 not_found; 4 bad_store

自检: python3 -B -m tasksvc.cli --selftest   (打印 PASS/FAIL, 0=通过)
"""

import json
import os
import sys
import tempfile
import time

if __package__ in (None, ""):  # 支持直接 python3 tasksvc/cli.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasksvc import service, store  # noqa: E402

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

STATUSES = ("open", "done", "expired", "all")


class UsageError(Exception):
    """用法错误: 未知子命令 / 未知选项 / 选项缺参。"""


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _parse_globals(argv):
    db = None
    now = None
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--db":
            i += 1
            if i >= len(argv):
                raise UsageError("--db requires a value")
            db = argv[i]
        elif tok == "--now":
            i += 1
            if i >= len(argv):
                raise UsageError("--now requires a value")
            now = _parse_now(argv[i])
        else:
            break
        i += 1
    return db, now, argv[i:]


def _parse_now(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise UsageError("--now must be a number")


def _parse_int(raw, name):
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise UsageError("%s must be an integer" % name)


def _parse_ttl(raw):
    try:
        ttl = float(raw)
    except (TypeError, ValueError):
        raise UsageError("--ttl must be a number")
    if ttl <= 0:
        raise UsageError("--ttl must be > 0")
    return ttl


def _resolve_now(now):
    """未提供 --now 时回落系统时钟。"""
    return time.time() if now is None else now


def _run(rest, db, now):
    now = _resolve_now(now)
    if not rest:
        raise UsageError("missing command")
    cmd = rest[0]
    args = rest[1:]

    # expire 需在加载前不依赖任何额外状态; 统一走 load。
    data = store.load(db) if db else {"next_id": 1, "tasks": []}

    if cmd == "add":
        text = None
        ttl = None
        i = 0
        while i < len(args):
            tok = args[i]
            if tok == "--ttl":
                i += 1
                if i >= len(args):
                    raise UsageError("--ttl requires a value")
                ttl = _parse_ttl(args[i])
            elif text is None:
                text = tok
            else:
                raise UsageError("unexpected argument")
            i += 1
        if text is None:
            raise UsageError("add requires <text>")
        out = service.cmd_add(data, text, ttl, now)

    elif cmd == "list":
        status = "open"
        i = 0
        while i < len(args):
            tok = args[i]
            if tok == "--status":
                i += 1
                if i >= len(args):
                    raise UsageError("--status requires a value")
                status = args[i]
                if status not in STATUSES:
                    raise UsageError("bad status")
            else:
                raise UsageError("unexpected argument")
            i += 1
        out = service.cmd_list(data, status, now)

    elif cmd == "done":
        if len(args) != 1:
            raise UsageError("done requires <id>")
        tid = _parse_int(args[0], "id")
        out = service.cmd_done(data, tid, now)

    elif cmd == "stats":
        if args:
            raise UsageError("unexpected argument")
        out = service.cmd_stats(data, now)

    elif cmd == "expire":
        if args:
            raise UsageError("unexpected argument")
        out = service.cmd_expire(data, now)

    else:
        raise UsageError("unknown command: %s" % cmd)

    if db:
        store.save(db, data)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "--selftest":
        return _selftest()

    try:
        db, now, rest = _parse_globals(argv)
        out = _run(rest, db, now)
    except UsageError:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except service.BadRequest:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except service.NotFound:
        _emit({"error": "not_found"})
        return EXIT_NOT_FOUND
    except store.BadStore:
        _emit({"error": "bad_store"})
        return EXIT_BAD_STORE

    _emit(out)
    return EXIT_OK


# --------------------------------------------------------------------------
# 自检: python3 -B -m tasksvc.cli --selftest
# 覆盖: 契约 1-9 的核心不变式与边界, 含负向控制。
# --------------------------------------------------------------------------

def _selftest():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    tmpdir = tempfile.mkdtemp(prefix="tasksvc-selftest-")

    def cli(*args):
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = main(list(args))
        finally:
            sys.stdout = old
        raw = buf.getvalue()
        obj = json.loads(raw)
        check("output is exactly one json line: %s" % (args,),
              raw.count("\n") == 1 and raw.endswith("\n"))
        return code, obj, raw

    # --- 契约 2/3: add 基本形态, 系统时钟回落 ---
    db = os.path.join(tmpdir, "a.json")
    code, obj, _ = cli("--db", db, "add", "hello")
    check("add rc=0", code == 0)
    check("add returns task", obj["task"]["id"] == 1 and obj["task"]["done"] is False
          and obj["task"]["expires_at"] is None)
    check("created_at is float now", isinstance(obj["task"]["created_at"], float))

    # --- 契约 7: text 逐字节保留 (中文/emoji/首尾空格) ---
    tricky = "  你好 😀  "
    code, obj, raw = cli("--db", db, "add", tricky)
    check("text round-trips byte-exact", obj["task"]["text"] == tricky)
    check("text not ascii-escaped in raw", "😀" in raw)

    # --- 契约 1: next_id 持久化且只增不减 ---
    with open(db, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    check("store has int next_id", isinstance(data["next_id"], int)
          and data["next_id"] == 3)
    check("store is utf-8 no BOM", not open(db, "rb").read(3) == b"\xef\xbb\xbf")

    # --- 契约 5/4: ttl 过期边界 now >= expires_at ---
    code, obj, _ = cli("--db", db, "--now", "100", "add", "withttl", "--ttl", "10")
    tid = obj["task"]["id"]
    check("ttl sets expires_at=now+ttl", obj["task"]["expires_at"] == 110.0)
    # now=109 未过期
    code, obj, _ = cli("--db", db, "--now", "109", "list", "--status", "expired")
    check("just before expiry not expired", obj["tasks"] == [])
    # now=110 恰好过期 (含等号)
    code, obj, _ = cli("--db", db, "--now", "110", "list", "--status", "expired")
    check("at expiry boundary expired", [t["id"] for t in obj["tasks"]] == [tid])

    # --- 契约 4: 过期优先于 done 互斥; done 视图排除已过期 ---
    cli("--db", db, "--now", "100", "done", str(tid))
    code, obj, _ = cli("--db", db, "--now", "200", "list", "--status", "done")
    check("expired task not in done view", all(t["id"] != tid for t in obj["tasks"]))
    code, obj, _ = cli("--db", db, "--now", "200", "list", "--status", "expired")
    check("done task still expired view", any(t["id"] == tid for t in obj["tasks"]))

    # --- 契约: 列表按 id 升序 ---
    code, obj, _ = cli("--db", db, "list", "--status", "all")
    ids = [t["id"] for t in obj["tasks"]]
    check("list sorted by id", ids == sorted(ids))

    # --- 契约 3: done 幂等 ---
    c1, _, _ = cli("--db", db, "--now", "100", "done", "1")
    c2, o2, _ = cli("--db", db, "--now", "100", "done", "1")
    check("done idempotent", c1 == 0 and c2 == 0 and o2["task"]["done"] is True)

    # --- 契约 3/4: stats 与视图一致性 ---
    code, obj, _ = cli("--db", db, "--now", "200", "stats")
    check("stats total==open+done+expired",
          obj["total"] == obj["open"] + obj["done"] + obj["expired"])
    check("stats expired counts", obj["expired"] == 1)

    # --- 契约 3: expire 真删除 + 契约 6 id 永不复用 ---
    code, obj, _ = cli("--db", db, "--now", "200", "expire")
    check("expire lists removed ids", obj["expired"] == [tid])
    code, obj, _ = cli("--db", db, "list", "--status", "all")
    check("expire really deletes", all(t["id"] != tid for t in obj["tasks"]))
    with open(db, "r", encoding="utf-8") as fh:
        nid = json.load(fh)["next_id"]
    code, obj, _ = cli("--db", db, "--now", "200", "add", "after-expire")
    check("deleted id not reused", obj["task"]["id"] == nid and obj["task"]["id"] > tid)

    # --- 契约 8: 退出码与错误输出 ---
    code, obj, _ = cli("--db", db, "add", "   ")
    check("blank text -> 2 bad_request", code == 2 and obj == {"error": "bad_request"})
    code, obj, _ = cli("--db", db, "done", "abc")
    check("non-int id -> 2 bad_request", code == 2 and obj == {"error": "bad_request"})
    code, obj, _ = cli("--db", db, "add", "x", "--ttl", "0")
    check("ttl<=0 -> 2 bad_request", code == 2 and obj == {"error": "bad_request"})
    code, obj, _ = cli("--db", db, "frobnicate")
    check("unknown cmd -> 2 bad_request", code == 2 and obj == {"error": "bad_request"})
    code, obj, _ = cli("--db", db, "done", "999999")
    check("unknown id -> 3 not_found", code == 3 and obj == {"error": "not_found"})

    # --- 契约 8/9: 坏存储 -> 4, 且不被破坏 ---
    bad = os.path.join(tmpdir, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("not-json{")
    before = open(bad, "r", encoding="utf-8").read()
    code, obj, _ = cli("--db", bad, "list")
    check("corrupt json -> 4 bad_store", code == 4 and obj == {"error": "bad_store"})
    check("corrupt store untouched", open(bad, "r", encoding="utf-8").read() == before)

    bad2 = os.path.join(tmpdir, "bad2.json")
    with open(bad2, "w", encoding="utf-8") as fh:
        json.dump({"next_id": "x", "tasks": []}, fh)
    code, obj, _ = cli("--db", bad2, "stats")
    check("bad schema -> 4 bad_store", code == 4 and obj == {"error": "bad_store"})

    # --- 契约 9: 原子写无临时残留 + 写入后文件始终完整 ---
    leftovers = [n for n in os.listdir(tmpdir) if n.startswith(".tasksvc-")]
    check("no temp file residue", leftovers == [])

    # --- 契约 6: 会话级单调性 (多次 add 递增) ---
    db3 = os.path.join(tmpdir, "c.json")
    seen = []
    for k in range(5):
        _, o, _ = cli("--db", db3, "add", "t%d" % k)
        seen.append(o["task"]["id"])
    check("ids strictly increasing", seen == sorted(seen) and len(set(seen)) == 5)

    # --- 负向控制: 篡改过期判据 (>= 改 >) 应导致边界用例变红 ---
    orig = service.is_expired
    try:
        def strict(task, now):
            exp = task.get("expires_at")
            return exp is not None and now > exp  # 去掉等号
        service._is_expired = strict
        _, o, _ = cli("--db", db, "--now", "110", "list", "--status", "expired")
        # 边界任务已被删除, 改用新库验证负控
        db4 = os.path.join(tmpdir, "neg.json")
        cli("--db", db4, "--now", "100", "add", "n", "--ttl", "10")
        _, o, _ = cli("--db", db4, "--now", "110", "list", "--status", "expired")
        check("negctl: boundary(==) must be expired", o["tasks"] == [])
    finally:
        service._is_expired = orig

    # 恢复后同一用例必须再次变绿
    db5 = os.path.join(tmpdir, "pos.json")
    cli("--db", db5, "--now", "100", "add", "p", "--ttl", "10")
    _, o, _ = cli("--db", db5, "--now", "110", "list", "--status", "expired")
    check("restored: boundary(==) expired again", len(o["tasks"]) == 1)

    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print("---- %d/%d passed ----" % (len(checks) - len(failed), len(checks)))
    print("SELFTEST " + ("PASS" if not failed else "FAIL"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
