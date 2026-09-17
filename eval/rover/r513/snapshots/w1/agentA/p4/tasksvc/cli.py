#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasksvc.cli — 任务队列 CLI 服务（仅标准库，Python 3）。

运行:
    python3 -B -m tasksvc.cli --db store.json --now 1000 add "写文档" --ttl 60
    python3 -B -m tasksvc.cli --db store.json --now 1000 list --status open
    python3 -B -m tasksvc.cli --db store.json --now 1060 stats
    python3 -B -m tasksvc.cli --db store.json expire
    python3 -B -m tasksvc.cli --selftest          # 运行文件内部自检（不读写外部 db）

约束:
  * 每条命令向 stdout 打印恰好一个 JSON 对象（ensure_ascii=False + 一个尾换行）。
  * 退出码: 成功 0 / 参数错 2 / 未知 id 3 / 存储损坏 4。
  * 存储写入原子（临时文件 + 同目录 os.replace），不留临时文件。
  * 时间判定只使用 --now 注入的时钟；缺失时回落 time.time()。
"""

import argparse
import json
import os
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# 退出码
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

# 缺省子命令缺省视图
DEFAULT_STATUS = "open"


class CliError(Exception):
    """带退出码与错误标签的受控异常。"""

    def __init__(self, code, label):
        super().__init__(label)
        self.code = code
        self.label = label


# ---------------------------------------------------------------------------
# 输出（唯一出口，保证"恰好一个 JSON 对象"）
# ---------------------------------------------------------------------------
def emit(obj):
    text = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def fail(code, label):
    emit({"error": label})
    return code


# ---------------------------------------------------------------------------
# 存储层
# ---------------------------------------------------------------------------
def _empty_store():
    return {"next_id": 1, "tasks": []}


def load_store(path):
    """读取并校验存储；返回 dict。缺失文件视为空表。损坏 -> CliError(bad_store)。"""
    if not os.path.exists(path):
        return _empty_store()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        raise CliError(EXIT_BAD_STORE, "bad_store")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise CliError(EXIT_BAD_STORE, "bad_store")
    return _validate(data)


def _validate(data):
    """schema 校验：顶层对象 + next_id 为正整数 + tasks 为合法列表。"""
    if not isinstance(data, dict):
        raise CliError(EXIT_BAD_STORE, "bad_store")
    nid = data.get("next_id")
    # 注意: bool 是 int 子类，需显式排除
    if isinstance(nid, bool) or not isinstance(nid, int) or nid < 1:
        raise CliError(EXIT_BAD_STORE, "bad_store")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise CliError(EXIT_BAD_STORE, "bad_store")
    max_id = 0
    for t in tasks:
        if not isinstance(t, dict):
            raise CliError(EXIT_BAD_STORE, "bad_store")
        tid = t.get("id")
        if isinstance(tid, bool) or not isinstance(tid, int) or tid < 1:
            raise CliError(EXIT_BAD_STORE, "bad_store")
        if not isinstance(t.get("text"), str):
            raise CliError(EXIT_BAD_STORE, "bad_store")
        if not isinstance(t.get("done"), bool):
            raise CliError(EXIT_BAD_STORE, "bad_store")
        created = t.get("created_at")
        if isinstance(created, bool) or not isinstance(created, (int, float)):
            raise CliError(EXIT_BAD_STORE, "bad_store")
        exp = t.get("expires_at")
        if exp is not None and (isinstance(exp, bool) or not isinstance(exp, (int, float))):
            raise CliError(EXIT_BAD_STORE, "bad_store")
        if tid > max_id:
            max_id = tid
    # next_id 只增不减: 若落后于现存最大 id 则视为损坏
    if nid <= max_id:
        raise CliError(EXIT_BAD_STORE, "bad_store")
    return {"next_id": nid, "tasks": tasks}


def save_store(path, store):
    """原子写入: 同目录临时文件 -> os.replace，且清理临时残留。"""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    payload = json.dumps(store, ensure_ascii=False, sort_keys=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, os.path.abspath(path))
        tmp_path = None  # 已改名，无需清理
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 视图 / 过期语义
# ---------------------------------------------------------------------------
def is_expired(task, now):
    exp = task.get("expires_at")
    # now >= expires_at 即过期；过期优先于 done。
    return exp is not None and now >= exp


def classify(task, now):
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def task_view(task):
    """对外视图: 只暴露契约约定的字段。"""
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


def sorted_tasks(store):
    return sorted(store["tasks"], key=lambda t: t["id"])


def find_task(store, task_id):
    for t in store["tasks"]:
        if t["id"] == task_id:
            return t
    return None


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
def cmd_add(store, now, args):
    text = args.text
    if text.strip() == "":
        raise CliError(EXIT_BAD_REQUEST, "bad_request")
    ttl = args.ttl
    if ttl is not None and ttl <= 0:
        raise CliError(EXIT_BAD_REQUEST, "bad_request")
    expires_at = None if ttl is None else (now + ttl)
    task = {
        "id": store["next_id"],
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": expires_at,
    }
    store["next_id"] += 1  # 只增不减，永不复用
    store["tasks"].append(task)
    return {"task": task_view(task)}


def cmd_list(store, now, args):
    status = args.status or DEFAULT_STATUS
    if status not in ("open", "done", "expired", "all"):
        raise CliError(EXIT_BAD_REQUEST, "bad_request")
    if status == "all":
        selected = sorted_tasks(store)
    else:
        selected = [t for t in sorted_tasks(store) if classify(t, now) == status]
    return {"tasks": [task_view(t) for t in selected]}


def cmd_done(store, now, args):
    task = find_task(store, args.id)
    if task is None:
        raise CliError(EXIT_NOT_FOUND, "not_found")
    task["done"] = True  # 幂等
    return {"task": task_view(task)}


def cmd_stats(store, now, args):
    counts = {"open": 0, "done": 0, "expired": 0}
    for t in store["tasks"]:
        counts[classify(t, now)] += 1
    return {
        "total": len(store["tasks"]),
        "open": counts["open"],
        "done": counts["done"],
        "expired": counts["expired"],
    }


def cmd_expire(store, now, args):
    expired_ids = [t["id"] for t in sorted_tasks(store) if is_expired(t, now)]
    if expired_ids:
        dead = set(expired_ids)
        store["tasks"] = [t for t in store["tasks"] if t["id"] not in dead]
    return {"expired": expired_ids}


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}

# 每条命令是否需要写回存储
WRITES = {"add": True, "list": False, "done": True, "stats": False, "expire": True}


# ---------------------------------------------------------------------------
# 参数解析（全局选项必须位于子命令之前）
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(prog="tasksvc", add_help=False)
    parser.add_argument("--db")
    parser.add_argument("--now")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("command", nargs="?")
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    return parser


def parse_now(raw):
    """--now 必须是整数或浮点 epoch 秒。"""
    if raw is None:
        return time.time()
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise CliError(EXIT_BAD_REQUEST, "bad_request")


def parse_sub(rest):
    """解析子命令参数，返回 (opts, positional)。"""
    opts = {"ttl": None, "status": None, "rest": []}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--ttl":
            if i + 1 >= len(rest):
                raise CliError(EXIT_BAD_REQUEST, "bad_request")
            try:
                opts["ttl"] = int(rest[i + 1])
            except (TypeError, ValueError):
                raise CliError(EXIT_BAD_REQUEST, "bad_request")
            i += 2
        elif tok == "--status":
            if i + 1 >= len(rest):
                raise CliError(EXIT_BAD_REQUEST, "bad_request")
            opts["status"] = rest[i + 1]
            i += 2
        else:
            opts["rest"].append(tok)
            i += 1
    return opts


def parse_id(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise CliError(EXIT_BAD_REQUEST, "bad_request")


def require_db(db):
    if not db:
        raise CliError(EXIT_BAD_REQUEST, "bad_request")


def dispatch(command, opts, now, store, args_namespace):
    if command == "add":
        if len(opts["rest"]) != 1:
            raise CliError(EXIT_BAD_REQUEST, "bad_request")
        ns = argparse.Namespace(text=opts["rest"][0], ttl=opts["ttl"])
        return cmd_add(store, now, ns)
    if command == "list":
        if opts["rest"]:
            raise CliError(EXIT_BAD_REQUEST, "bad_request")
        ns = argparse.Namespace(status=opts["status"])
        return cmd_list(store, now, ns)
    if command == "done":
        if len(opts["rest"]) != 1:
            raise CliError(EXIT_BAD_REQUEST, "bad_request")
        ns = argparse.Namespace(id=parse_id(opts["rest"][0]))
        return cmd_done(store, now, ns)
    if command == "stats":
        if opts["rest"]:
            raise CliError(EXIT_BAD_REQUEST, "bad_request")
        return cmd_stats(store, now, None)
    if command == "expire":
        if opts["rest"]:
            raise CliError(EXIT_BAD_REQUEST, "bad_request")
        return cmd_expire(store, now, None)
    raise CliError(EXIT_BAD_REQUEST, "bad_request")


def run(argv):
    parser = build_parser()
    try:
        namespace = parser.parse_args(argv)
    except SystemExit:
        return fail(EXIT_BAD_REQUEST, "bad_request")

    if namespace.selftest:
        return _selftest()

    now = parse_now(namespace.now)
    if not namespace.command:
        raise CliError(EXIT_BAD_REQUEST, "bad_request")
    if namespace.command not in COMMANDS:
        raise CliError(EXIT_BAD_REQUEST, "bad_request")

    require_db(namespace.db)
    store = load_store(namespace.db)
    opts = parse_sub(namespace.rest)
    result = dispatch(namespace.command, opts, now, store, namespace)
    if WRITES[namespace.command]:
        save_store(namespace.db, store)
    emit(result)
    return EXIT_OK


# ---------------------------------------------------------------------------
# 无头自检（--selftest）：覆盖契约的每一条非功能语义
# ---------------------------------------------------------------------------
def _selftest():
    failures = []

    def check(name, cond):
        if cond:
            print("  ok   " + name)
        else:
            failures.append(name)
            print("  FAIL " + name)

    def run_main(argv):
        """在子进程内真实执行一次 CLI，返回 (rc, stdout, stderr)。"""
        import subprocess
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        key = os.environ.get("TASKSVC_SELFTEST_KEY", "")
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "tasksvc.cli"] + argv,
            capture_output=True,
            cwd=_pkg_root(),
            env=env,
        )
        return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")

    def one_json(out):
        lines = out.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        if len(lines) != 1:
            return None
        try:
            return json.loads(lines[0])
        except ValueError:
            return None

    workdir = tempfile.mkdtemp(prefix="tasksvc-selftest-")
    db = os.path.join(workdir, "store.json")

    # 1) add + text 逐字节往返（中文/emoji/首尾空格）
    text = "  写文档 🚀  "
    rc, out, err = run_main(["--db", db, "--now", "1000", "add", text, "--ttl", "60"])
    obj = one_json(out)
    check("add rc=0", rc == 0)
    check("add 单 JSON 输出", obj is not None)
    check("add text 逐字节往返", obj and obj["task"]["text"] == text)
    check("add expires_at=now+ttl", obj and obj["task"]["expires_at"] == 1060.0)
    check("add created_at=now", obj and obj["task"]["created_at"] == 1000.0)

    # 2) 空 text -> bad_request(2)
    rc, out, _ = run_main(["--db", db, "--now", "1000", "add", "   "])
    check("空白 text -> rc 2", rc == EXIT_BAD_REQUEST)
    check("空白 text -> bad_request", one_json(out) == {"error": "bad_request"})

    # 3) ttl<=0 -> bad_request
    rc, out, _ = run_main(["--db", db, "--now", "1000", "add", "x", "--ttl", "0"])
    check("ttl=0 -> bad_request", rc == EXIT_BAD_REQUEST and one_json(out) == {"error": "bad_request"})
    rc, out, _ = run_main(["--db", db, "--now", "1000", "add", "x", "--ttl", "-5"])
    check("ttl<0 -> bad_request", rc == EXIT_BAD_REQUEST and one_json(out) == {"error": "bad_request"})

    # 4) 未知子命令 -> bad_request
    rc, out, _ = run_main(["--db", db, "--now", "1000", "bogus"])
    check("未知子命令 -> bad_request", rc == EXIT_BAD_REQUEST and one_json(out) == {"error": "bad_request"})

    # 5) 过期优先于 done：task1 在 now=1060 过期
    rc, out, _ = run_main(["--db", db, "--now", "1060", "list", "--status", "open"])
    check("now>=expires_at -> open 为空", one_json(out) == {"tasks": []})
    rc, out, _ = run_main(["--db", db, "--now", "1060", "list", "--status", "expired"])
    check("expired 视图含 id=1", one_json(out)["tasks"][0]["id"] == 1)
    rc, out, _ = run_main(["--db", db, "--now", "1059", "list", "--status", "open"])
    check("边界前 open 含 id=1", one_json(out)["tasks"][0]["id"] == 1)

    # 6) done 幂等 + 未过期任务
    rc, out, _ = run_main(["--db", db, "--now", "1010", "add", "second"])
    second_id = one_json(out)["task"]["id"]
    rc, out, _ = run_main(["--db", db, "--now", "1011", "done", str(second_id)])
    check("done rc=0", rc == 0 and one_json(out)["task"]["done"] is True)
    rc, out, _ = run_main(["--db", db, "--now", "1012", "done", str(second_id)])
    check("done 幂等 rc=0", rc == 0 and one_json(out)["task"]["done"] is True)

    # 7) 未知 id -> not_found(3)
    rc, out, _ = run_main(["--db", db, "--now", "1012", "done", "9999"])
    check("未知 id -> rc 3", rc == EXIT_NOT_FOUND)
    check("未知 id -> not_found", one_json(out) == {"error": "not_found"})
    rc, out, _ = run_main(["--db", db, "--now", "1012", "done", "abc"])
    check("非整数 id -> bad_request", rc == EXIT_BAD_REQUEST and one_json(out) == {"error": "bad_request"})

    # 8) stats 口径
    rc, out, _ = run_main(["--db", db, "--now", "1060", "stats"])
    st = one_json(out)
    check("stats 汇总一致", st["total"] == st["open"] + st["done"] + st["expired"])
    check("stats expired=1", st["expired"] == 1)

    # 9) expire 真删除 + id 不复用
    rc, out, _ = run_main(["--db", db, "--now", "1060", "expire"])
    check("expire 返回 id 列表", one_json(out) == {"expired": [1]})
    with open(db, "r", encoding="utf-8") as fh:
        disk = json.load(fh)
    check("expire 后磁盘 tasks 不含 id=1", all(t["id"] != 1 for t in disk["tasks"]))
    check("next_id 只增不减", disk["next_id"] >= second_id + 1)
    rc, out, _ = run_main(["--db", db, "--now", "1060", "add", "third"])
    check("删除后 id 不复用", one_json(out)["task"]["id"] > second_id)

    # 10) 未提供 --now 回落系统时钟、不报错
    rc, out, _ = run_main(["--db", os.path.join(workdir, "b.json"), "add", "no-clock"])
    check("缺省 --now 回落系统时钟", rc == 0 and one_json(out) is not None)

    # 11) 存储损坏（非 JSON / schema 不符）-> bad_store(4)
    bad = os.path.join(workdir, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    rc, out, _ = run_main(["--db", bad, "--now", "1000", "list"])
    check("非 JSON -> rc 4", rc == EXIT_BAD_STORE and one_json(out) == {"error": "bad_store"})
    with open(bad, "w", encoding="utf-8") as fh:
        json.dump({"next_id": 0, "tasks": []}, fh)
    rc, out, _ = run_main(["--db", bad, "--now", "1000", "list"])
    check("schema 不符 -> bad_store", rc == EXIT_BAD_STORE and one_json(out) == {"error": "bad_store"})

    # 12) list 默认 open + 按 id 升序
    rc, out, _ = run_main(["--db", db, "--now", "1060", "list"])
    ids = [t["id"] for t in one_json(out)["tasks"]]
    check("list 默认 open 且升序", ids == sorted(ids))

    # 13) 原子性 / 无临时残留
    leftovers = [n for n in os.listdir(workdir) if n.startswith(".tasksvc-")]
    check("无临时文件残留", leftovers == [])

    # 14) stdout 恰好一个 JSON 对象（不得有其它内容）
    rc, out, err = run_main(["--db", db, "--now", "1060", "stats"])
    check("stdout 恰一个 JSON", one_json(out) is not None and err == "")

    # 清理
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)

    print("")
    if failures:
        print("SELFTEST FAIL ({0} 项失败)".format(len(failures)))
        for name in failures:
            print("  - " + name)
        return 1
    print("SELFTEST PASS")
    return 0


def _pkg_root():
    """返回包所在父目录，用于子进程以 -m 方式导入 tasksvc。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return run(argv)
    except CliError as exc:
        return fail(exc.code, exc.label)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_BAD_REQUEST
        return fail(EXIT_BAD_REQUEST, "bad_request") if code != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
