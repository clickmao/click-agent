"""Command line interface for the task queue service.

Usage::

    python3 -B -m tasksvc.cli --db <path> --now <epoch> <command> [...]
"""

from __future__ import annotations

import json
import sys

from . import storage
from .storage import BadStore

USAGE = (
    "usage: tasksvc --db <path> --now <epoch> <command> [args]\n"
    "commands: add <text> [--ttl <seconds>] | list [--status <s>] | "
    "done <id> | stats | expire"
)

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


class BadRequest(Exception):
    pass


def _to_float(value, what):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise BadRequest("%s must be a number" % what)


def _to_int(value, what):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise BadRequest("%s must be an integer" % what)


def _is_expired(task, now):
    expires_at = task["expires_at"]
    return expires_at is not None and now >= expires_at


def _is_open(task, now):
    return not task["done"] and not _is_expired(task, now)


def _recompute(store, now):
    counts = {"total": 0, "open": 0, "done": 0, "expired": 0}
    for task in store["tasks"]:
        counts["total"] += 1
        if _is_expired(task, now):
            counts["expired"] += 1
        elif task["done"]:
            counts["done"] += 1
        else:
            counts["open"] += 1
    return counts


def _parse_global(argv):
    db = None
    now = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--db":
            if index + 1 >= len(argv):
                raise BadRequest("--db requires a value")
            if db is not None:
                raise BadRequest("--db given more than once")
            db = argv[index + 1]
            index += 2
        elif token == "--now":
            if index + 1 >= len(argv):
                raise BadRequest("--now requires a value")
            if now is not None:
                raise BadRequest("--now given more than once")
            now = _to_float(argv[index + 1], "--now")
            index += 2
        elif token.startswith("--db="):
            if db is not None:
                raise BadRequest("--db given more than once")
            db = token[len("--db="):]
            index += 1
        elif token.startswith("--now="):
            if now is not None:
                raise BadRequest("--now given more than once")
            now = _to_float(token[len("--now="):], "--now")
            index += 1
        else:
            break
    if db is None:
        raise BadRequest("--db is required")
    if now is None:
        raise BadRequest("--now is required")
    return db, now, argv[index:]


def _cmd_add(store, now, args):
    if not args:
        raise BadRequest("add requires <text>")
    text = args[0]
    ttl = None
    index = 1
    while index < len(args):
        token = args[index]
        if token == "--ttl":
            if index + 1 >= len(args):
                raise BadRequest("--ttl requires a value")
            ttl = _to_float(args[index + 1], "--ttl")
            index += 2
        elif token.startswith("--ttl="):
            ttl = _to_float(token[len("--ttl="):], "--ttl")
            index += 1
        else:
            raise BadRequest("unexpected argument: %s" % token)
    if ttl is not None and ttl <= 0:
        raise BadRequest("--ttl must be positive")
    if text.strip() == "":
        raise BadRequest("text must not be blank")
    task = {
        "id": store["next_id"],
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": None if ttl is None else now + ttl,
    }
    store["next_id"] += 1
    store["tasks"].append(task)
    store["tasks"].sort(key=lambda t: t["id"])
    return {"task": task}


def _cmd_list(store, now, args):
    status = "open"
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--status":
            if index + 1 >= len(args):
                raise BadRequest("--status requires a value")
            status = args[index + 1]
            index += 2
        elif token.startswith("--status="):
            status = token[len("--status="):]
            index += 1
        else:
            raise BadRequest("unexpected argument: %s" % token)
    if status not in ("open", "done", "expired", "all"):
        raise BadRequest("invalid status: %s" % status)
    if status == "all":
        selected = list(store["tasks"])
    elif status == "expired":
        selected = [t for t in store["tasks"] if _is_expired(t, now)]
    elif status == "done":
        selected = [
            t for t in store["tasks"] if t["done"] and not _is_expired(t, now)
        ]
    else:
        selected = [t for t in store["tasks"] if _is_open(t, now)]
    selected.sort(key=lambda t: t["id"])
    return {"tasks": selected}


def _cmd_done(store, now, args):
    if len(args) != 1:
        raise BadRequest("done requires exactly one <id>")
    task_id = _to_int(args[0], "id")
    for task in store["tasks"]:
        if task["id"] == task_id:
            task["done"] = True
            return {"task": task}
    raise KeyError(task_id)


def _cmd_stats(store, now, args):
    if args:
        raise BadRequest("stats takes no arguments")
    return _recompute(store, now)


def _cmd_expire(store, now, args):
    if args:
        raise BadRequest("expire takes no arguments")
    expired = [t for t in store["tasks"] if _is_expired(t, now)]
    expired.sort(key=lambda t: t["id"])
    keep = [t for t in store["tasks"] if not _is_expired(t, now)]
    store["tasks"] = keep
    return {"expired": [t["id"] for t in expired]}


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    try:
        db, now, rest = _parse_global(argv)
        if not rest:
            raise BadRequest("missing command")
        command, args = rest[0], rest[1:]
        if command not in ("add", "list", "done", "stats", "expire"):
            raise BadRequest("unknown command: %s" % command)
        store = storage.load(db)
        try:
            if command == "add":
                result = _cmd_add(store, now, args)
            elif command == "list":
                result = _cmd_list(store, now, args)
            elif command == "done":
                result = _cmd_done(store, now, args)
            elif command == "stats":
                result = _cmd_stats(store, now, args)
            else:
                result = _cmd_expire(store, now, args)
        except KeyError:
            _emit({"error": "not_found"})
            return EXIT_NOT_FOUND
        storage.save(db, store)
        _emit(result)
        return EXIT_OK
    except BadRequest:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except BadStore:
        _emit({"error": "bad_store"})
        return EXIT_BAD_STORE


if __name__ == "__main__":
    raise SystemExit(main())
