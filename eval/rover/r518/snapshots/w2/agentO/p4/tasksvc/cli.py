"""tasksvc.cli —— 命令行入口 / 命令状态机 / 输出与退出码 (第 3 段职责)。

本段职责 (节点 n3):
  3) 全局选项 `--db`/`--now` 写在子命令**之前**。每条命令结束必须向 stdout
     打印恰好一个 JSON 对象 (ensure_ascii=False, 可带一个尾换行), 不得打印
     其它内容。命令集合:
       add <text> [--ttl <秒>]  -> {"task": {...}}
       list [--status open|done|expired|all] -> {"tasks": [...]}   (缺省 open)
       done <id>                -> {"task": {...}}   幂等: 已 done 再 done 仍成功
       stats                    -> {"total","open","done","expired"}
       expire                   -> {"expired": [id, ...]}  并把已过期任务真删除
  5) `--ttl N` 创建时 expires_at = now + N; now >= expires_at 即为已过期。
  6) id 单调、永不复用: 已删除 / 已过期的 id 不得再次分配 (next_id 只增不减)。
  7) text 逐字节保留 (中文/emoji/首尾空格原样往返); 去首尾空白后为空 = 参数错。
  8) 退出码: 成功 0; 参数/用法错 -> 2 + {"error":"bad_request"};
     未知 id -> 3 + {"error":"not_found"}; 存储损坏 -> 4 + {"error":"bad_store"}。

边界: 存储读写复用 n1 的 store.py; 时钟与视图复用 n2 的 model.py。
本段不重写这两块逻辑。

运行:
    python3 -B -m tasksvc.cli --db <path> [--now <epoch秒>] <子命令> ...
    python3 -B -m tasksvc.cli --selftest        # 无头自检, PASS 退出码 0 / FAIL 退出码 1
"""
from __future__ import annotations

import json
import sys

from . import model
from . import store

__all__ = ["main", "PROG"]

PROG = "tasksvc.cli"

# 退出码 (契约 8)
EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

# 全局选项名。契约要求它们出现在子命令**之前**。
GLOBAL_OPTS = ("--db", "--now")

# 子命令集合。未知子命令 -> bad_request。
COMMANDS = ("add", "list", "done", "stats", "expire")


# --------------------------------------------------------------------------
# 内部异常: 只用于在 main() 内部区分失败类别, 绝不逃逸到调用方
# --------------------------------------------------------------------------
class UsageError(Exception):
    """参数/用法错 -> 退出码 2, 输出 {"error":"bad_request"}。"""


class NotFoundError(Exception):
    """未知 id -> 退出码 3, 输出 {"error":"not_found"}。"""


# --------------------------------------------------------------------------
# 全局选项切分 (--db/--now 必须在子命令之前)
# --------------------------------------------------------------------------
def split_global_options(argv):
    """把 argv 切成 (globals, rest)。

    只吃子命令**之前**的 --db/--now。遇到第一个非全局选项 token 即视为
    子命令起点, 余下原样交给子命令解析器。
    全局选项必须带值 (--db PATH / --now SEC); 重复出现以后者为准。
    """
    opts = {"db": None, "now": None}
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if tok == "--":
            # 显式终止全局选项区
            return opts, argv[i + 1:]
        if not tok.startswith("--"):
            return opts, argv[i:]
        name, sep, inline = tok.partition("=")
        if name not in GLOBAL_OPTS:
            # 未知的全局选项 -> 用法错 (它在子命令之前, 归全局解析器管)
            raise UsageError("未知全局选项: %s" % tok)
        key = name[2:]
        if sep:
            value = inline
        else:
            if i + 1 >= n:
                raise UsageError("全局选项 %s 缺少取值" % name)
            value = argv[i + 1]
            i += 1
        if key == "db":
            opts["db"] = value
        else:
            opts["now"] = parse_now(value)
        i += 1
    return opts, []


def parse_now(raw):
    """解析 --now 的值 (数字字符串) -> float。非法 -> 用法错。"""
    text = raw.strip()
    if not text:
        raise UsageError("--now 不能为空")
    try:
        # int/float 都接受; bool 语义不适用 (命令行不会出现 True/False)
        value = float(text)
    except ValueError:
        raise UsageError("--now 必须是数字 (epoch 秒): %r" % raw)
    if value != value:  # NaN
        raise UsageError("--now 不能是 NaN")
    try:
        model.resolve_now(value)  # 复用 n2 的校验 (异常 -> 用法错)
    except ValueError as exc:
        raise UsageError(str(exc))
    return value


def parse_positive_ttl(raw):
    """解析 --ttl 的值 -> float > 0。<= 0 或非数字 -> 用法错。"""
    text = raw.strip()
    if not text:
        raise UsageError("--ttl 不能为空")
    try:
        value = float(text)
    except ValueError:
        raise UsageError("--ttl 必须是数字 (秒): %r" % raw)
    if value != value:
        raise UsageError("--ttl 不能是 NaN")
    if value <= 0:
        raise UsageError("--ttl 必须 > 0: %r" % raw)
    return value


def parse_id(raw):
    """解析任务 id -> int >= 1。非整数 / <= 0 -> 用法错。"""
    if isinstance(raw, bool) or not isinstance(raw, str):
        raise UsageError("id 必须是整数")
    text = raw.strip()
    try:
        value = int(text)
    except (TypeError, ValueError):
        raise UsageError("id 必须是整数: %r" % raw)
    if value < 1:
        raise UsageError("id 必须 >= 1: %r" % raw)
    return value


# --------------------------------------------------------------------------
# 任务视图
# --------------------------------------------------------------------------
def task_to_view(task):
    """存储中的 task -> 输出用 task (字段顺序固定, expires_at 保留 null)。"""
    expires_at = task.get("expires_at")
    return {
        "id": int(task["id"]),
        "text": task["text"],
        "done": bool(task["done"]),
        "created_at": float(task["created_at"]),
        "expires_at": None if expires_at is None else float(expires_at),
    }


def selected(rest, now):
    """解析 list 的 --status (缺省 open), 返回按 id 升序的任务列表。"""
    view = model.DEFAULT_VIEW
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("--status", "-s"):
            if i + 1 >= len(rest):
                raise UsageError("%s 缺少取值" % tok)
            view = rest[i + 1]
            i += 2
            continue
        if tok.startswith("--status="):
            view = tok.split("=", 1)[1]
            i += 1
            continue
        raise UsageError("list 未知选项: %s" % tok)
    if view not in model.VIEWS:
        raise UsageError("--status 非法: %r" % (view,))
    return view


# --------------------------------------------------------------------------
# 子命令处理器 (每个返回 (exit_code, payload))
# --------------------------------------------------------------------------
def cmd_add(state, now, rest):
    """add <text> [--ttl <秒>] -> 新建任务, id = next_id (只增不减)。"""
    text = None
    ttl = None
    i = 0
    while i < len(rest):
        tok = rest[i]
        if not tok.startswith("--") and text is None:
            text = tok
            i += 1
            continue
        if tok == "--ttl":
            if i + 1 >= len(rest):
                raise UsageError("--ttl 缺少取值")
            ttl = parse_positive_ttl(rest[i + 1])
            i += 2
            continue
        if tok.startswith("--ttl="):
            ttl = parse_positive_ttl(tok.split("=", 1)[1])
            i += 1
            continue
        raise UsageError("add 未知参数: %s" % tok)

    if text is None:
        raise UsageError("add 缺少 <text>")
    # 契约 7: 去首尾空白后为空 = 参数错; 原文本逐字节保留
    if text.strip() == "":
        raise UsageError("text 去首尾空白后为空")

    tid = int(state["next_id"])
    state["next_id"] = tid + 1  # 只增不减, 覆盖已 done / 已删除的 id
    task = {
        "id": tid,
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": None if ttl is None else float(now) + ttl,
    }
    state["tasks"].append(task)
    # 落盘由 drive() 在命令成功后统一执行
    return EXIT_OK, {"task": task_to_view(task)}


def cmd_list(state, now, rest):
    """list [--status open|done|expired|all] -> 按 id 升序的任务列表。"""
    view = selected(rest, now)
    tasks = model.visible_tasks(state["tasks"], now, view)
    return EXIT_OK, {"tasks": [task_to_view(t) for t in tasks]}


def cmd_done(state, now, rest):
    """done <id> -> 置 done (幂等: 已 done 再 done 仍成功)。"""
    if len(rest) != 1:
        raise UsageError("done 需要且只需要一个 <id>")
    tid = parse_id(rest[0])
    target = None
    for task in state["tasks"]:
        if int(task["id"]) == tid:
            target = task
            break
    if target is None:
        raise NotFoundError("id 不存在: %s" % tid)
    target["done"] = True  # 幂等: 已是 True 再写仍为 True
    return EXIT_OK, {"task": task_to_view(target)}


def cmd_stats(state, now, rest):
    """stats -> {"total","open","done","expired"}。

    口径 (契约 4): expired 优先于 done, 三类互斥; total = 存储中全部任务数。
    """
    if rest:
        raise UsageError("stats 不接受参数: %s" % " ".join(rest))
    counts = {"open": 0, "done": 0, "expired": 0}
    for task in state["tasks"]:
        counts[model.classify(task, now)] += 1
    payload = {
        "total": len(state["tasks"]),
        "open": counts["open"],
        "done": counts["done"],
        "expired": counts["expired"],
    }
    return EXIT_OK, payload


def cmd_expire(state, now, rest):
    """expire -> 真删除已过期任务, 返回被删除的 id (升序)。"""
    if rest:
        raise UsageError("expire 不接受参数: %s" % " ".join(rest))
    doomed = model.expired_ids(state["tasks"], now)
    doomed_set = set(doomed)
    if doomed_set:
        state["tasks"] = [t for t in state["tasks"] if int(t["id"]) not in doomed_set]
    return EXIT_OK, {"expired": [int(x) for x in sorted(doomed_set)]}


HANDLERS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}

# 会写盘 (且修改了持久化状态) 的命令
WRITE_COMMANDS = ("add", "done", "expire")


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------
def emit(payload):
    """向 stdout 打印恰好一个 JSON 对象 (ensure_ascii=False + 一个尾换行)。"""
    text = json.dumps(payload, ensure_ascii=False)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def drive(argv, db_path, now_value):
    """执行一条命令。

    返回 (exit_code, payload, state_changed)。
    state_changed 决定是否需要写盘 (只读命令不触碰文件)。
    """
    state = store.load(db_path) if db_path else store.empty_state()
    now = model.Clock(now_value).now()

    if not argv:
        raise UsageError("缺少子命令")
    command = argv[0]
    if command not in COMMANDS:
        raise UsageError("未知子命令: %s" % command)
    rest = argv[1:]

    code, payload = HANDLERS[command](state, now, rest)
    state_changed = command in WRITE_COMMANDS
    if state_changed and db_path:
        store.save(db_path, state)
    return code, payload, state_changed


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv=None):
    """命令行入口。返回进程退出码 (0/2/3/4)。只输出一个 JSON 对象。"""
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    if argv and argv[0] == "--selftest":
        return run_selftest()

    try:
        opts, rest = split_global_options(argv)
    except UsageError:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    try:
        code, payload, _ = drive(rest, opts["db"], opts["now"])
    except UsageError:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except store.BadStore:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE
    except NotFoundError:
        emit({"error": "not_found"})
        return EXIT_NOT_FOUND

    emit(payload)
    return code


# --------------------------------------------------------------------------
# 无头自检: 真跑子进程 + 真读写 db 文件, 逐条核对 stdout JSON 与退出码
# --------------------------------------------------------------------------
def _run_cli(args, cwd):
    """在子进程中真跑 `python3 -B -m tasksvc.cli ...`。

    返回 (exit_code, stdout_bytes)。stdout 必须是合法 UTF-8。
    """
    import subprocess

    cmd = [sys.executable, "-B", "-m", "tasksvc.cli"] + list(args)
    proc = subprocess.run(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _decode_json(raw, label):
    """把子进程 stdout 解成 (text, obj)。要求恰好一个 JSON 对象 + 可选尾换行。"""
    text = raw.decode("utf-8")  # 非 UTF-8 直接抛
    body = text[:-1] if text.endswith("\n") else text
    if "\n" in body or "\r" in body:
        raise AssertionError("%s: stdout 出现多余行/回车: %r" % (label, text))
    obj = json.loads(body)
    if not isinstance(obj, dict):
        raise AssertionError("%s: stdout 顶层不是 JSON 对象: %r" % (label, text))
    return text, obj


def run_selftest():
    """端到端自检: 经真实入口驱动, 覆盖契约 1/2/3/4/5/6/7/8/9。

    打印 "SELFTEST PASS N/N" (退出码 0) 或 "SELFTEST FAIL ..." (退出码 1)。
    """
    import io
    import os
    import shutil
    import tempfile

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmpdir = tempfile.mkdtemp(prefix="tasksvc-cli-selftest-")
    db = os.path.join(tmpdir, "sub", "tasks.json")  # 故意多一层目录: 验 makedirs
    checks = []

    def ok(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    def call(args, expect_code):
        code, out, err = _run_cli(args, root)
        text, obj = _decode_json(out, args[0] if args else "?")
        ok("exit(%s)=%d" % (" ".join(args), expect_code), code == expect_code,
           "got %d, stdout=%r stderr=%r" % (code, text, err.decode("utf-8", "replace")))
        if err:
            # 任何 stderr 输出都是污染 (契约 3: 不得打印其它内容)
            ok("stderr empty(%s)" % " ".join(args), False, repr(err))
        return code, obj

    try:
        # --- 空库: 缺省 (无 --now) 回落系统时钟, 不得报错 -------
        call(["--db", db, "list"], 0)

        # --- add + 缺省 now (系统时钟) -------------------------
        base = 1000.0
        code, a1 = call(["--db", db, "--now", repr(base), "add", "  中文🙂  "], 0)
        ok("add.next_id starts at 1", a1["task"]["id"] == 1, repr(a1))
        ok("text byte-preserved", a1["task"]["text"] == "  中文🙂  ", repr(a1))
        ok("created_at = now", a1["task"]["created_at"] == base, repr(a1))
        ok("no ttl -> expires_at null", a1["task"]["expires_at"] is None, repr(a1))
        ok("fresh task not done", a1["task"]["done"] is False, repr(a1))

        # --- ttl 边界: now >= expires_at 即过期 ----------------
        call(["--db", db, "--now", repr(base), "add", "ttl30", "--ttl", "30"], 0)
        call(["--db", db, "--now", repr(base), "add", "ttl10", "--ttl", "10"], 0)
        # now = base+30 恰好 == expires_at(30) -> 过期 (等号即过期)
        code, s1 = call(["--db", db, "--now", repr(base + 30), "stats"], 0)
        # 等号即过期: ttl30 的 expires_at == base+30 == now -> expired;
        # ttl10 更早已过 -> expired。恰好 2 个过期, 1 个仍 open。
        ok("boundary now==expires_at counts expired", s1["expired"] == 2, repr(s1))
        ok("stats total", s1["total"] == 3, repr(s1))
        ok("stats open", s1["open"] == 1, repr(s1))
        ok("stats done", s1["done"] == 0, repr(s1))

        # --- id 单调: 已过期 id 不得复用 -----------------------
        code, a4 = call(["--db", db, "--now", repr(base), "add", "after-expire"], 0)
        ok("id never reused (next=4)", a4["task"]["id"] == 4, repr(a4))

        # --- 视图: 过期优先于 done (互斥) ----------------------
        call(["--db", db, "--now", repr(base), "done", "2"], 0)  # 2 有 ttl30
        code, l_exp = call(["--db", db, "--now", repr(base + 30), "list", "--status", "expired"], 0)
        # 过期优先于 done: id2 既 done 又过期 -> 只出现在 expired, 不在 done。
        ok("expired beats done", [t["id"] for t in l_exp["tasks"]] == [2, 3], repr(l_exp))
        code, l_done = call(["--db", db, "--now", repr(base + 30), "list", "--status", "done"], 0)
        # done 视图排除「已过期但曾 done」的 id2 (过期优先, 互斥)。
        ok("done view excludes expired-done", [t["id"] for t in l_done["tasks"]] == [], repr(l_done))

        # --- 列表按 id 升序 (与写入顺序无关) --------------------
        code, l_open = call(["--db", db, "--now", repr(base + 30), "list"], 0)
        ids = [t["id"] for t in l_open["tasks"]]
        # 缺省 open: id1 (未 done 未过期) + id4 (未 done 未过期); id2/3 已过期。
        ok("list default=open sorted by id", ids == [1, 4], repr(l_open))
        code, l_all = call(["--db", db, "--now", repr(base + 30), "list", "--status", "all"], 0)
        ok("all view sorted by id", [t["id"] for t in l_all["tasks"]] == [1, 2, 3, 4], repr(l_all))

        # --- done 幂等 ----------------------------------------
        code, d1 = call(["--db", db, "--now", repr(base), "done", "1"], 0)
        code, d2 = call(["--db", db, "--now", repr(base), "done", "1"], 0)
        ok("done idempotent (both 0)", code == 0 and d1["task"]["done"] and d2["task"]["done"],
           repr((d1, d2)))

        # --- expire 真删除 ------------------------------------
        code, e1 = call(["--db", db, "--now", repr(base + 100), "expire"], 0)
        ok("expire returns ids", e1["expired"] == [2, 3], repr(e1))
        code, l_all2 = call(["--db", db, "--now", repr(base + 100), "list", "--status", "all"], 0)
        ok("expire really deletes", [t["id"] for t in l_all2["tasks"]] == [1, 4], repr(l_all2))
        code, e2 = call(["--db", db, "--now", repr(base + 100), "expire"], 0)
        ok("expire idempotent (empty)", e2["expired"] == [], repr(e2))

        # --- 退出码 2: 空白 text ------------------------------
        call(["--db", db, "--now", "1", "add", "   "], 2)
        call(["--db", db, "--now", "1", "add", "\t\n"], 2)
        # --- 退出码 2: --ttl <= 0 -----------------------------
        call(["--db", db, "--now", "1", "add", "x", "--ttl", "0"], 2)
        call(["--db", db, "--now", "1", "add", "x", "--ttl", "-5"], 2)
        # --- 退出码 2: 非整数 id ------------------------------
        call(["--db", db, "--now", "1", "done", "abc"], 2)
        call(["--db", db, "--now", "1", "done", "1.5"], 2)
        # --- 退出码 2: 未知子命令 -----------------------------
        call(["--db", db, "--now", "1", "frobnicate"], 2)
        # --- 退出码 2: 非法 --status / 非法 --now -------------
        call(["--db", db, "--now", "1", "list", "--status", "bogus"], 2)
        call(["--db", db, "--now", "notanumber", "list"], 2)
        # --- 退出码 3: 未知 id --------------------------------
        call(["--db", db, "--now", "1", "done", "999"], 3)

        # --- 退出码 4: 存储损坏 -------------------------------
        broken = os.path.join(tmpdir, "broken.json")
        with io.open(broken, "w", encoding="utf-8", newline="") as fh:
            fh.write("{not json")
        call(["--db", broken, "list"], 4)
        bad_schema = os.path.join(tmpdir, "schema.json")
        with io.open(bad_schema, "w", encoding="utf-8", newline="") as fh:
            fh.write('{"tasks": []}')  # 缺 next_id
        call(["--db", bad_schema, "list"], 4)

        # --- 负向控制: bad_store 与 not_found 的载荷必须不同 ---
        code, ebad = call(["--db", broken, "list"], 4)
        ok("bad_store payload", ebad == {"error": "bad_store"}, repr(ebad))
        code, enot = call(["--db", db, "--now", "1", "done", "999"], 3)
        ok("not_found payload", enot == {"error": "not_found"}, repr(enot))
        code, ebr = call(["--db", db, "--now", "1", "add", ""], 2)
        ok("bad_request payload", ebr == {"error": "bad_request"}, repr(ebr))

        # --- 契约 9: 写盘后无临时文件残留; 文件是完整 JSON -----
        leftovers = [n for n in os.listdir(os.path.dirname(db))
                     if n.startswith(".tasksvc-tmp-")]
        ok("no tmp leftovers", leftovers == [], repr(leftovers))
        with io.open(db, "r", encoding="utf-8") as fh:
            raw = fh.read()
        saved = json.loads(raw)  # 非法 JSON 会抛
        ok("db is complete JSON object", isinstance(saved, dict) and
           isinstance(saved["next_id"], int), raw[:80])
        ok("next_id never decreases", saved["next_id"] == 5, repr(saved["next_id"]))
        ok("db has no BOM", not raw.startswith("\ufeff"), "starts with U+FEFF")

        # --- 契约 7: emoji/中文 跨进程往返逐字节一致 -----------
        code, rt = call(["--db", db, "--now", repr(base), "list", "--status", "all"], 0)
        gotten = [t["text"] for t in rt["tasks"] if t["id"] == 1]
        ok("unicode round-trip via file", gotten == ["  中文🙂  "], repr(gotten))
    except Exception as exc:  # 自检自身出错也必须判 FAIL
        checks.append(("selftest-harness", False, "%s: %s" % (type(exc).__name__, exc)))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(checks)
    failed = [(n, d) for n, c, d in checks if not c]
    for name, cond, detail in checks:
        if not cond:
            sys.stdout.write("FAIL %s :: %s\n" % (name, detail))
    if failed:
        sys.stdout.write("SELFTEST FAIL %d/%d\n" % (total - len(failed), total))
        sys.stdout.flush()
        return 1
    sys.stdout.write("SELFTEST PASS %d/%d\n" % (total, total))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
