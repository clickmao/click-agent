"""任务队列 CLI 服务 —— 入口。

用法（全局选项写在子命令之前）:
    python3 -B -m tasksvc.cli --db <path> --now <epoch> <subcommand> [args]

子命令:
    add <text> [--ttl <秒>]            -> {"task": {...}}
    list [--status open|done|expired|all] -> {"tasks": [...]}  (缺省 open)
    done <id>                          -> {"task": {...}}  (幂等)
    stats                              -> {"total","open","done","expired"}
    expire                             -> {"expired":[id,...]}  并真删除

stdout 每条命令恰好打印一个 JSON 对象（ensure_ascii=False）+ 一个尾换行。
退出码: 0 成功 / 2 bad_request / 3 not_found / 4 bad_store。

自检: python3 -B -m tasksvc.cli --selftest   (# 打印 PASS/FAIL, 0=通过)
"""

import json
import os
import sys

from . import store
from .model import counts, is_expired, select, view_of

# 允许的子命令与状态
SUBCMDS = ("add", "list", "done", "stats", "expire")
STATUSES = ("open", "done", "expired", "all")


class BadRequest(Exception):
    """用法/参数错误 -> 退出码 2。"""


class NotFound(Exception):
    """未知 id -> 退出码 3。"""


def _out(obj):
    """打印唯一一个 JSON 对象 + 尾换行。"""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ------------------------- 参数解析 -------------------------

def _split_global(argv):
    """解析 --db / --now（必须出现在子命令之前）。"""
    db_path = None
    now = None
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in SUBCMDS:
            break
        if tok == "--db":
            if i + 1 >= len(argv):
                raise BadRequest("--db needs value")
            db_path = argv[i + 1]
            i += 2
        elif tok == "--now":
            if i + 1 >= len(argv):
                raise BadRequest("--now needs value")
            try:
                now = float(argv[i + 1])
            except ValueError:
                raise BadRequest("--now must be number")
            i += 2
        else:
            raise BadRequest("unknown global option: %r" % tok)
    return db_path, now, argv[i:]


def _parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        raise BadRequest("not an int: %r" % s)


# ------------------------- 子命令 -------------------------

def cmd_add(db, now, args):
    text = None
    ttl = None
    i = 0
    while i < len(args):
        if args[i] == "--ttl":
            if i + 1 >= len(args):
                raise BadRequest("--ttl needs value")
            try:
                ttl = float(args[i + 1])
            except ValueError:
                raise BadRequest("--ttl must be number")
            if ttl <= 0:
                raise BadRequest("--ttl must be > 0")
            i += 2
        elif text is None:
            text = args[i]
            i += 1
        else:
            raise BadRequest("unexpected arg: %r" % args[i])
    if text is None or text.strip() == "":
        raise BadRequest("empty text")
    task = {
        "id": db["next_id"],
        "text": text,  # 逐字节保留（中文/emoji/首尾空格）
        "done": False,
        "created_at": float(now),
        "expires_at": (None if ttl is None else float(now) + float(ttl)),
    }
    db["next_id"] += 1  # 只增不减：删除/过期后也不复用
    db["tasks"].append(task)
    return {"task": task}


def cmd_list(db, now, args):
    status = "open"
    i = 0
    while i < len(args):
        if args[i] == "--status":
            if i + 1 >= len(args):
                raise BadRequest("--status needs value")
            status = args[i + 1]
            if status not in STATUSES:
                raise BadRequest("bad status: %r" % status)
            i += 2
        else:
            raise BadRequest("unexpected arg: %r" % args[i])
    return {"tasks": select(db["tasks"], status, now)}


def cmd_done(db, now, args):
    if len(args) != 1:
        raise BadRequest("done needs exactly one id")
    tid = _parse_int(args[0])
    for t in db["tasks"]:
        if t["id"] == tid:
            t["done"] = True  # 幂等
            return {"task": t}
    raise NotFound(str(tid))


def cmd_stats(db, now, args):
    if args:
        raise BadRequest("stats takes no args")
    return counts(db["tasks"], now)


def cmd_expire(db, now, args):
    if args:
        raise BadRequest("expire takes no args")
    expired_ids = [t["id"] for t in db["tasks"] if is_expired(t, now)]
    expired_ids.sort()
    db["tasks"] = [t for t in db["tasks"] if not is_expired(t, now)]  # 真删除
    return {"expired": expired_ids}


HANDLERS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}


def dispatch(argv, db_path):
    """执行一条命令，返回 (result_dict, db)；异常由调用方处理。"""
    db_path, now, rest = _split_global(argv)
    if now is None:
        raise BadRequest("--now is required")
    if db_path is None:
        raise BadRequest("--db is required")
    if not rest or rest[0] not in SUBCMDS:
        raise BadRequest("unknown subcommand")
    db = store.load(db_path)
    result = HANDLERS[rest[0]](db, now, rest[1:])
    store.save(db_path, db)
    return result, db


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        from .selftest import run_selftest
        return run_selftest()

    db_path = None
    try:
        # 预取 db 路径以便错误也能确定存储（解析阶段可能先失败）
        try:
            db_path, _now, _rest = _split_global(argv)
        except BadRequest:
            pass
        result, _db = dispatch(argv, db_path)
    except BadRequest:
        _out({"error": "bad_request"})
        return store.EXIT_BAD_REQUEST
    except store.StoreError:
        _out({"error": "bad_store"})
        return store.EXIT_BAD_STORE
    except NotFound:
        _out({"error": "not_found"})
        return store.EXIT_NOT_FOUND
    _out(result)
    return store.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
