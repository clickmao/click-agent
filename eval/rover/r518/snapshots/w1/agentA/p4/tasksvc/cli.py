#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasksvc.cli —— 任务队列 CLI 服务（仅 Python 3 标准库，无第三方依赖）。

运行:
    python3 -B -m tasksvc.cli [--db <path>] [--now <epoch 秒>] <子命令> [参数...]

子命令:
    add <text> [--ttl <秒>]                     -> {"task": {...}}
    list [--status open|done|expired|all]       -> {"tasks": [...]}   缺省 open
    done <id>                                   -> {"task": {...}}  幂等
    stats                                       -> {"total":..,"open":..,"done":..,"expired":..}
    expire                                      -> {"expired": [id, ...]}  真删除

契约要点:
    * 全局选项 --db/--now 必须写在子命令之前；--now 缺省回落 time.time()，不报错。
    * 每条命令向 stdout 打印**恰好一个** JSON 对象（ensure_ascii=False + 一个尾换行），无其它输出。
    * 退出码: 0 成功 / 2 参数·用法错 / 3 未知 id / 4 存储损坏。
    * 存储写入原子: 同目录临时文件 + os.fsync + os.replace，异常时清理临时文件。
    * id 单调、永不复用: 由持久化字段 next_id 保证，过期/删除都不会回收 id。
"""

import json
import math
import os
import re
import sys
import tempfile
import time

# ---------------------------------------------------------------- 退出码 / 错误

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

_STATUSES = ("open", "done", "expired", "all")
_INT_RE = re.compile(r"^-?\d+$")


class CliError(Exception):
    """携带退出码与错误码的受控失败。"""

    def __init__(self, code, error):
        super().__init__(error)
        self.code = code
        self.error = error


def _bad_request():
    return CliError(EXIT_BAD_REQUEST, "bad_request")


def _not_found():
    return CliError(EXIT_NOT_FOUND, "not_found")


def _bad_store():
    return CliError(EXIT_BAD_STORE, "bad_store")


# ---------------------------------------------------------------- 类型判定工具


def _is_real_int(value):
    """真正的整数（bool 是 int 子类，必须排除）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_real_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------- 存储读写


def _valid_task(task):
    if not isinstance(task, dict):
        return False
    if not _is_real_int(task.get("id")):
        return False
    if not isinstance(task.get("text"), str):
        return False
    if not isinstance(task.get("done"), bool):
        return False
    if not _is_real_num(task.get("created_at")):
        return False
    expires_at = task.get("expires_at")
    if expires_at is not None and not _is_real_num(expires_at):
        return False
    return True


def load_store(db_path):
    """读取存储，返回 (next_id, {id: task})；文件不存在视为空库。"""
    if not os.path.exists(db_path):
        return 1, {}
    try:
        with open(db_path, "rb") as handle:
            raw = handle.read()
    except OSError:
        raise _bad_store()
    try:
        text = raw.decode("utf-8-sig")  # 容忍带 BOM 的读取；写出永远是 UTF-8 无 BOM
    except UnicodeDecodeError:
        raise _bad_store()
    if text.strip() == "":
        raise _bad_store()
    try:
        data = json.loads(text)
    except ValueError:
        raise _bad_store()
    if not isinstance(data, dict):
        raise _bad_store()

    next_id = data.get("next_id")
    if not _is_real_int(next_id) or next_id < 0:
        raise _bad_store()

    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list):
        raise _bad_store()

    tasks = {}
    for item in raw_tasks:
        if not _valid_task(item):
            raise _bad_store()
        task_id = int(item["id"])
        if task_id in tasks:
            raise _bad_store()
        tasks[task_id] = {
            "id": task_id,
            "text": item["text"],
            "done": bool(item["done"]),
            "created_at": float(item["created_at"]),
            "expires_at": None if item["expires_at"] is None else float(item["expires_at"]),
        }
    return int(next_id), tasks


def dump_store(next_id, tasks):
    """序列化存储内容（字段顺序稳定，UTF-8，尾换行）。"""
    ordered = [tasks[key] for key in sorted(tasks)]
    payload = {"next_id": int(next_id), "tasks": ordered}
    return json.dumps(payload, ensure_ascii=False, sort_keys=False) + "\n"


def atomic_write(db_path, text):
    """临时文件 + fsync + 同目录 os.replace：读者任一时点看到的都是完整 JSON。"""
    path = os.path.abspath(db_path)
    directory = os.path.dirname(path) or os.curdir
    os.makedirs(directory, exist_ok=True)
    handle_fd, tmp_path = tempfile.mkstemp(prefix=".tasksvc-tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _allocate_id(next_id, tasks):
    """新 id 由 next_id 单调推进；对人工构造的越界 next_id 做一次防碰撞加固。"""
    new_id = next_id if next_id >= 1 else 1
    while new_id in tasks:
        new_id += 1
    return new_id


# ---------------------------------------------------------------- 视图语义


def _is_expired(task, now):
    expires_at = task["expires_at"]
    return expires_at is not None and now >= expires_at


def _in_view(task, status, now):
    expired = _is_expired(task, now)
    if status == "open":
        return (not task["done"]) and (not expired)
    if status == "done":
        return task["done"] and (not expired)   # 过期优先于 done
    if status == "expired":
        return expired
    return True                                  # all


def task_json(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": float(task["created_at"]),
        "expires_at": None if task["expires_at"] is None else float(task["expires_at"]),
    }


# ---------------------------------------------------------------- 参数解析


def _parse_now(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise _bad_request()
    if not math.isfinite(parsed):
        raise _bad_request()
    return parsed


def _parse_globals(argv):
    """解析子命令之前的全局选项，返回 (db, now, 剩余参数)。"""
    db_path = None
    now = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--db":
            index += 1
            if index >= len(argv):
                raise _bad_request()
            db_path = argv[index]
        elif arg.startswith("--db="):
            db_path = arg[5:]
        elif arg == "--now":
            index += 1
            if index >= len(argv):
                raise _bad_request()
            now = _parse_now(argv[index])
        elif arg.startswith("--now="):
            now = _parse_now(arg[6:])
        elif arg.startswith("--") and arg != "--":
            raise _bad_request()
        else:
            break
        index += 1
    if db_path is None or db_path == "":
        raise _bad_request()
    return db_path, now, argv[index:]


def _parse_ttl(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise _bad_request()
    if not math.isfinite(parsed) or parsed <= 0:
        raise _bad_request()
    return parsed


def _parse_add(args):
    text = None
    ttl = None
    positional_only = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--" and not positional_only:
            positional_only = True
        elif not positional_only and arg == "--ttl":
            index += 1
            if index >= len(args):
                raise _bad_request()
            ttl = _parse_ttl(args[index])
        elif not positional_only and arg.startswith("--ttl="):
            ttl = _parse_ttl(arg[6:])
        elif not positional_only and arg.startswith("--"):
            raise _bad_request()
        else:
            if text is not None:
                raise _bad_request()
            text = arg
        index += 1
    if text is None:
        raise _bad_request()
    if text.strip() == "":
        raise _bad_request()
    return text, ttl


def _parse_list(args):
    status = "open"
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--status":
            index += 1
            if index >= len(args):
                raise _bad_request()
            status = args[index]
        elif arg.startswith("--status="):
            status = arg[9:]
        else:
            raise _bad_request()
        index += 1
    if status not in _STATUSES:
        raise _bad_request()
    return status


def _parse_id(args):
    if len(args) != 1:
        raise _bad_request()
    if not _INT_RE.match(args[0]):
        raise _bad_request()
    return int(args[0], 10)


# ---------------------------------------------------------------- 子命令


def _cmd_add(db_path, now, args):
    text, ttl = _parse_add(args)
    next_id, tasks = load_store(db_path)
    new_id = _allocate_id(next_id, tasks)
    task = {
        "id": new_id,
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": None if ttl is None else float(now) + float(ttl),
    }
    tasks[new_id] = task
    atomic_write(db_path, dump_store(new_id + 1, tasks))
    return {"task": task_json(task)}


def _cmd_list(db_path, now, args):
    status = _parse_list(args)
    _next_id, tasks = load_store(db_path)
    selected = [task for _key, task in sorted(tasks.items()) if _in_view(task, status, now)]
    return {"tasks": [task_json(task) for task in selected]}


def _cmd_done(db_path, now, args):
    target = _parse_id(args)
    next_id, tasks = load_store(db_path)
    task = tasks.get(target)
    if task is None:
        raise _not_found()
    if not task["done"]:
        task["done"] = True
        atomic_write(db_path, dump_store(next_id, tasks))
    return {"task": task_json(task)}


def _cmd_stats(db_path, now, args):
    if args:
        raise _bad_request()
    _next_id, tasks = load_store(db_path)
    counts = {"total": len(tasks), "open": 0, "done": 0, "expired": 0}
    for task in tasks.values():
        for status in ("open", "done", "expired"):
            if _in_view(task, status, now):
                counts[status] += 1
                break
    return counts


def _cmd_expire(db_path, now, args):
    if args:
        raise _bad_request()
    next_id, tasks = load_store(db_path)
    expired_ids = sorted(key for key, task in tasks.items() if _is_expired(task, now))
    if expired_ids:
        for key in expired_ids:
            del tasks[key]
        atomic_write(db_path, dump_store(next_id, tasks))
    return {"expired": expired_ids}


_COMMANDS = {
    "add": _cmd_add,
    "list": _cmd_list,
    "done": _cmd_done,
    "stats": _cmd_stats,
    "expire": _cmd_expire,
}


def run(argv):
    db_path, now_opt, rest = _parse_globals(argv)
    if not rest:
        raise _bad_request()
    command, args = rest[0], rest[1:]
    handler = _COMMANDS.get(command)
    if handler is None:
        raise _bad_request()
    now = now_opt if now_opt is not None else time.time()
    return handler(db_path, now, args)


# ---------------------------------------------------------------- 输出 / 入口


def emit(obj):
    """打印恰好一个 JSON 对象（ensure_ascii=False，UTF-8，一个尾换行）。"""
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
    stream = getattr(sys.stdout, "buffer", None)
    if stream is None:                                   # 被替换为文本流时（测试友好）
        sys.stdout.write(data.decode("utf-8"))
        sys.stdout.flush()
    else:
        stream.write(data)
        stream.flush()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        result = run(list(argv))
        code = EXIT_OK
    except CliError as err:
        result = {"error": err.error}
        code = err.code
    except (OSError, UnicodeError):
        result = {"error": "bad_store"}
        code = EXIT_BAD_STORE
    emit(result)
    return code


if __name__ == "__main__":
    sys.exit(main())
