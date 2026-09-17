#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasksvc.cli —— 任务队列 CLI 服务 (Python 3 标准库, 零第三方依赖)。

用法:
    python3 -B -m tasksvc.cli --db <path> --now <epoch秒> <command> [args]

全局选项 --db / --now 必须写在子命令之前。

子命令:
    add <text> [--ttl <秒>]    -> {"task": {...}}
    list [--status open|done|expired|all]  -> {"tasks": [...]}  缺省 open
    done <id>                  -> {"task": {...}}   幂等
    stats                      -> {"total":int,"open":int,"done":int,"expired":int}
    expire                     -> {"expired":[<id>, ...]}  真删除

输出契约: 每条命令结束向 stdout 打印恰好一个 JSON 对象 (ensure_ascii=False),
可带一个尾换行; 不得打印其它内容。

退出码:
    0 成功; 2 参数/用法错 {"error":"bad_request"};
    3 未知 id {"error":"not_found"}; 4 存储损坏 {"error":"bad_store"}。

存储: --db 指向一个 JSON 文件, 形如
    {"next_id": 1, "tasks": [ {task}, ... ]}
task 字段: id:int, text:str, done:bool, created_at:float, expires_at:float|null

时间: 所有时间判定只使用 --now 注入的时钟, 绝不调用 time.sleep / 真实时钟。
过期语义: expires_at IS NOT NULL 且 now >= expires_at 即为已过期;
         过期优先于 done (open / done / expired 三视图互斥)。

原子写: 写同目录临时文件 -> os.replace() 原子重命名, 不留临时文件残留。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 退出码
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

VALID_STATUSES = ("open", "done", "expired", "all")


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def emit(obj: Dict[str, Any]) -> None:
    """向 stdout 打印恰好一个 JSON 对象 (UTF-8, 非 ASCII 原样)。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def fail(code: int, err: str, detail: str = "") -> int:
    """输出错误对象并返回退出码。"""
    payload: Dict[str, Any] = {"error": err}
    if detail:
        payload["detail"] = detail
    emit(payload)
    return code


# ---------------------------------------------------------------------------
# 存储
# ---------------------------------------------------------------------------
class BadStore(Exception):
    """存储文件非 JSON 或 schema 不符。"""


class Store:
    """JSON 文件存储 (next_id + tasks 列表), 读写均原子。"""

    @staticmethod
    def path_str(db_path: str) -> str:
        # 一律用绝对路径, 不假设当前工作目录。
        return os.path.abspath(db_path)

    @staticmethod
    def validate(data: Any) -> Dict[str, Any]:
        """校验并规范化存储内容, 不符则抛 BadStore。"""
        if not isinstance(data, dict):
            raise BadStore("root is not a JSON object")
        if "next_id" not in data or not isinstance(data["next_id"], int) \
                or isinstance(data["next_id"], bool):
            raise BadStore("missing/invalid integer next_id")
        tasks = data.get("tasks", [])
        if not isinstance(tasks, list):
            raise BadStore("tasks is not a list")
        seen_ids = set()
        for t in tasks:
            if not isinstance(t, dict):
                raise BadStore("task is not an object")
            tid = t.get("id")
            if not isinstance(tid, int) or isinstance(tid, bool):
                raise BadStore("task.id is not an integer")
            if not isinstance(t.get("text"), str):
                raise BadStore("task.text is not a string")
            if not isinstance(t.get("done"), bool):
                raise BadStore("task.done is not a bool")
            if not _is_number(t.get("created_at")):
                raise BadStore("task.created_at is not a number")
            exp = t.get("expires_at", None)
            if exp is not None and not _is_number(exp):
                raise BadStore("task.expires_at is not a number/null")
            if tid in seen_ids:
                raise BadStore("duplicate task id")
            seen_ids.add(tid)
        if data["next_id"] < 1:
            raise BadStore("next_id must be >= 1")
        return {"next_id": data["next_id"], "tasks": tasks}

    @staticmethod
    def load(db_path: str) -> Dict[str, Any]:
        """读取存储; 文件不存在 => 全新空存储。"""
        path = Store.path_str(db_path)
        if not os.path.exists(path):
            return {"next_id": 1, "tasks": []}
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            raise BadStore("cannot read store: %s" % exc)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise BadStore("store is not valid UTF-8: %s" % exc)
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise BadStore("store is not valid JSON: %s" % exc)
        return Store.validate(data)

    @staticmethod
    def save(db_path: str, data: Dict[str, Any]) -> None:
        """原子写入: 同目录临时文件 + os.replace, 不留残留。"""
        path = Store.path_str(db_path)
        parent = os.path.dirname(path) or os.curdir
        if not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(data, fh, ensure_ascii=False, sort_keys=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)  # 同文件系统内原子替换
            tmp = None
        finally:
            if tmp is not None and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


def _is_number(v: Any) -> bool:
    """bool 不算数字。"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _f(v: Any) -> float:
    """规范化为 float (整数输入也返回 float)。"""
    return float(v)


# ---------------------------------------------------------------------------
# 领域逻辑
# ---------------------------------------------------------------------------
def is_expired(task: Dict[str, Any], now: float) -> bool:
    """now >= expires_at 即为已过期。"""
    exp = task.get("expires_at", None)
    if exp is None:
        return False
    return now >= _f(exp)


def view_of(task: Dict[str, Any], now: float) -> str:
    """互斥视图: 过期优先于 done。"""
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def task_out(task: Dict[str, Any]) -> Dict[str, Any]:
    """输出视图: created_at 为 float, expires_at 为 float|null。"""
    exp = task.get("expires_at", None)
    return {
        "id": task["id"],
        "text": task["text"],
        "done": bool(task["done"]),
        "created_at": _f(task["created_at"]),
        "expires_at": None if exp is None else _f(exp),
    }


# ---------------------------------------------------------------------------
# 参数解析 (手工解析: 全局选项必须位于子命令之前)
# ---------------------------------------------------------------------------
class Usage(Exception):
    """参数/用法错误。"""


def parse_argv(argv: List[str]) -> Tuple[str, float, str, List[str]]:
    """解析全局选项与子命令名, 返回 (db_path, now, command, rest)。

    全局 --db / --now 必须出现在子命令之前。遇到第一个非选项 token
    即认为是子命令, 其后所有 token 原样交给子命令解析器。
    """
    db_path: Optional[str] = None
    now: Optional[float] = None
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if tok == "--db":
            if i + 1 >= n:
                raise Usage("--db requires a value")
            db_path = argv[i + 1]
            i += 2
        elif tok.startswith("--db="):
            db_path = tok[len("--db="):]
            i += 1
        elif tok == "--now":
            if i + 1 >= n:
                raise Usage("--now requires a value")
            now = _parse_now(argv[i + 1])
            i += 2
        elif tok.startswith("--now="):
            now = _parse_now(tok[len("--now="):])
            i += 1
        elif tok.startswith("-"):
            raise Usage("unknown global option: %s" % tok)
        else:
            break
    if now is None:
        raise Usage("--now is required")
    db_path = db_path if db_path is not None else "tasksvc.json"
    if i >= n:
        raise Usage("missing subcommand")
    command = argv[i]
    return db_path, now, command, argv[i + 1:]


def _parse_now(raw: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise Usage("--now must be a number")


def _parse_int(raw: str, what: str) -> int:
    """严格十进制整数解析 (拒绝 1.0 / 0x1 / 带符号之外的杂项)。"""
    s = raw.strip()
    if s.startswith("+") or s.startswith("-"):
        body = s[1:]
    else:
        body = s
    if not body.isdigit():
        raise Usage("%s must be an integer" % what)
    return int(s)


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
def cmd_add(store: Dict[str, Any], now: float, args: List[str]) -> int:
    text: Optional[str] = None
    ttl: Optional[float] = None
    i = 0
    n = len(args)
    while i < n:
        tok = args[i]
        if tok == "--ttl":
            if i + 1 >= n:
                raise Usage("--ttl requires a value")
            ttl = _parse_ttl(args[i + 1])
            i += 2
        elif tok.startswith("--ttl="):
            ttl = _parse_ttl(tok[len("--ttl="):])
            i += 1
        elif tok.startswith("-") and text is None:
            # 允许 text 以 '-' 开头的情况仅当已用 -- 分隔, 这里按用法错处理
            raise Usage("unknown option for add: %s" % tok)
        elif text is None:
            text = tok
            i += 1
        else:
            raise Usage("unexpected extra argument for add: %s" % tok)
    if text is None:
        raise Usage("add requires <text>")
    if not text.strip():
        raise Usage("text must not be blank")
    # text 逐字节原样保留 (不做任何 strip)
    task_id = store["next_id"]
    store["next_id"] = task_id + 1  # 只增不减, 永不复用
    expires_at: Optional[float] = None
    if ttl is not None:
        expires_at = now + ttl
    task = {
        "id": task_id,
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": expires_at,
    }
    store["tasks"].append(task)
    return EXIT_OK


def _parse_ttl(raw: str) -> float:
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise Usage("--ttl must be a number")
    if not (val > 0):
        raise Usage("--ttl must be > 0")
    return val


def cmd_list(store: Dict[str, Any], now: float, args: List[str]) -> int:
    status = "open"
    i = 0
    n = len(args)
    while i < n:
        tok = args[i]
        if tok == "--status":
            if i + 1 >= n:
                raise Usage("--status requires a value")
            status = args[i + 1]
            i += 2
        elif tok.startswith("--status="):
            status = tok[len("--status="):]
            i += 1
        else:
            raise Usage("unexpected argument for list: %s" % tok)
    if status not in VALID_STATUSES:
        raise Usage("invalid status: %s" % status)
    tasks = sorted(store["tasks"], key=lambda t: t["id"])
    if status != "all":
        tasks = [t for t in tasks if view_of(t, now) == status]
    emit({"tasks": [task_out(t) for t in tasks]})
    return EXIT_OK


def cmd_done(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if len(args) != 1:
        raise Usage("done requires exactly one <id>")
    task_id = _parse_int(args[0], "<id>")
    for t in store["tasks"]:
        if t["id"] == task_id:
            t["done"] = True  # 幂等: 已 done 再 done 仍成功
            emit({"task": task_out(t)})
            return EXIT_OK
    return EXIT_NOT_FOUND


def cmd_stats(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if args:
        raise Usage("stats takes no arguments")
    total = len(store["tasks"])
    counts = {"open": 0, "done": 0, "expired": 0}
    for t in store["tasks"]:
        counts[view_of(t, now)] += 1
    emit({
        "total": total,
        "open": counts["open"],
        "done": counts["done"],
        "expired": counts["expired"],
    })
    return EXIT_OK


def cmd_expire(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if args:
        raise Usage("expire takes no arguments")
    expired_ids = sorted(
        t["id"] for t in store["tasks"] if is_expired(t, now)
    )
    if expired_ids:
        expired_set = set(expired_ids)
        # 真删除 (而不是仅标记)
        store["tasks"] = [t for t in store["tasks"] if t["id"] not in expired_set]
    emit({"expired": expired_ids})
    return EXIT_OK


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
DISPATCH = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}
# 需要写盘的命令
WRITES = {"add", "done", "expire"}


def run(argv: List[str]) -> int:
    try:
        db_path, now, command, rest = parse_argv(argv)
    except Usage:
        return fail(EXIT_BAD_REQUEST, "bad_request")

    handler = DISPATCH.get(command)
    if handler is None:
        return fail(EXIT_BAD_REQUEST, "bad_request")

    try:
        store = Store.load(db_path)
    except BadStore:
        return fail(EXIT_BAD_STORE, "bad_store")

    try:
        code = handler(store, now, rest)
    except Usage:
        return fail(EXIT_BAD_REQUEST, "bad_request")

    if code == EXIT_OK and command in WRITES:
        try:
            Store.save(db_path, store)
        except OSError:
            return fail(EXIT_BAD_STORE, "bad_store")
    return code


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
