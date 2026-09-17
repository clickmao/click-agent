"""tasksvc 命令行入口。

用法::

    python3 -B -m tasksvc.cli [--db PATH] [--now EPOCH] <subcommand> [args]

子命令:
    add <text> [--ttl SECONDS]        新增任务(文本逐字节保留)
    list [--status open|done|expired|all]  列出任务(缺省 open, 按 id 升序)
    done <id>                         标记完成(幂等)
    stats                             统计
    expire                            删除已过期任务并返回其 id

退出码:
    0 成功; 2 参数/用法错(bad_request); 3 未知 id(not_found); 4 存储损坏(bad_store)

约束: 只使用标准库; 每条命令向 stdout 打印恰好一个 JSON 对象; 不做 sleep;
      全局选项 --db/--now 必须写在子命令之前。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from . import core

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

SUBCOMMANDS = ("add", "list", "done", "stats", "expire")
STATUSES = ("open", "done", "expired", "all")


class BadRequest(Exception):
    """参数/用法错误。"""


def _emit(obj: Dict[str, Any]) -> None:
    """向 stdout 打印恰好一个 JSON 对象(UTF-8, 无 BOM)。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.write("\n")


def _parse_now(raw: Optional[str]) -> float:
    if raw is None:
        raise BadRequest("--now is required")
    try:
        now = float(raw)
    except (TypeError, ValueError):
        raise BadRequest("--now must be a number")
    if now != now or now in (float("inf"), float("-inf")):
        raise BadRequest("--now must be finite")
    return now


def _parse_id(raw: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise BadRequest("id must be an integer")
    if value < 1:
        raise BadRequest("id must be positive")
    return value


def _split_argv(argv: List[str]) -> Dict[str, Any]:
    """先解析子命令之前的全局选项, 再保留其后参数。"""
    db: Optional[str] = None
    now_raw: Optional[str] = None
    i = 0
    while i < len(argv):
        token = argv[i]
        if token not in ("--db", "--now"):
            break
        if i + 1 >= len(argv):
            raise BadRequest("missing value for global option")
        value = argv[i + 1]
        if token == "--db":
            db = value
        else:
            now_raw = value
        i += 2
    rest = argv[i:]
    if not rest:
        raise BadRequest("missing subcommand")
    sub = rest[0]
    if sub not in SUBCOMMANDS:
        raise BadRequest("unknown subcommand")
    return {
        "db": db,
        "now_raw": now_raw,
        "sub": sub,
        "args": rest[1:],
    }


def _cmd_add(store: Dict[str, Any], now: float, args: List[str]) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(prog="add", add_help=False)
    parser.add_argument("text")
    parser.add_argument("--ttl", type=str, default=None)
    try:
        ns = parser.parse_args(args)
    except SystemExit:
        raise BadRequest("bad add arguments")

    text = ns.text
    if text.strip() == "":
        raise BadRequest("text must not be blank")

    expires_at: Optional[float] = None
    if ns.ttl is not None:
        try:
            ttl = float(ns.ttl)
        except (TypeError, ValueError):
            raise BadRequest("ttl must be a number")
        if ttl != ttl or ttl in (float("inf"), float("-inf")) or ttl <= 0:
            raise BadRequest("ttl must be > 0")
        expires_at = now + ttl

    tid = store["next_id"]
    store["next_id"] = tid + 1
    task = {
        "id": tid,
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": expires_at,
    }
    store["tasks"].append(task)
    return {"task": core.normalize_task(task)}


def _cmd_list(store: Dict[str, Any], now: float, args: List[str]) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(prog="list", add_help=False)
    parser.add_argument("--status", type=str, default="open")
    try:
        ns = parser.parse_args(args)
    except SystemExit:
        raise BadRequest("bad list arguments")
    if ns.status not in STATUSES:
        raise BadRequest("bad status")
    chosen = core.select(store["tasks"], ns.status, now)
    return {"tasks": [core.normalize_task(t) for t in chosen]}


def _cmd_done(store: Dict[str, Any], now: float, args: List[str]) -> Dict[str, Any]:
    if len(args) != 1:
        raise BadRequest("done requires exactly one id")
    tid = _parse_id(args[0])
    task = core.find_by_id(store["tasks"], tid)
    if task is None:
        raise NotFoundError("no such id")
    # 幂等: 已 done 再 done 仍成功。
    task["done"] = True
    return {"task": core.normalize_task(task)}


def _cmd_stats(store: Dict[str, Any], now: float, args: List[str]) -> Dict[str, Any]:
    if args:
        raise BadRequest("stats takes no arguments")
    tasks = store["tasks"]
    expired = sum(1 for t in tasks if core.view_of(t, now) == "expired")
    done = sum(1 for t in tasks if core.view_of(t, now) == "done")
    open_count = sum(1 for t in tasks if core.view_of(t, now) == "open")
    return {
        "total": len(tasks),
        "open": open_count,
        "done": done,
        "expired": expired,
    }


def _cmd_expire(store: Dict[str, Any], now: float, args: List[str]) -> Dict[str, Any]:
    if args:
        raise BadRequest("expire takes no arguments")
    tasks = store["tasks"]
    expired_ids = sorted(t["id"] for t in tasks if core.is_expired(t, now))
    if expired_ids:
        gone = set(expired_ids)
        store["tasks"] = [t for t in tasks if t["id"] not in gone]
    return {"expired": expired_ids}


class NotFoundError(Exception):
    """未知 id。"""


HANDLERS = {
    "add": _cmd_add,
    "list": _cmd_list,
    "done": _cmd_done,
    "stats": _cmd_stats,
    "expire": _cmd_expire,
}


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    try:
        parsed = _split_argv(list(argv))
    except BadRequest:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    # 存储加载先于参数细节校验之外的一切副作用判定: 损坏优先报 bad_store。
    try:
        store = core.load_store(parsed["db"]) if parsed["db"] else core._empty_store()
    except core.BadStore:
        _emit({"error": "bad_store"})
        return EXIT_BAD_STORE

    try:
        now = _parse_now(parsed["now_raw"])
        handler = HANDLERS[parsed["sub"]]
        result = handler(store, now, parsed["args"])
    except NotFoundError:
        _emit({"error": "not_found"})
        return EXIT_NOT_FOUND
    except BadRequest:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    # 仅在有变更可能的子命令上落盘(仍是无条件覆盖, 保证 next_id 持久化)。
    if parsed["db"] and parsed["sub"] in ("add", "done", "expire"):
        core.save_store(parsed["db"], store)

    _emit(result)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
