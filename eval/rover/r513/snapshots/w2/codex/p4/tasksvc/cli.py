"""Task queue CLI (standard library only)."""

import argparse
import json
import os
import sys
import tempfile
import time

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


class BadRequest(Exception):
    pass


class BadStore(Exception):
    pass


def _error(exit_code, kind):
    sys.stdout.write(json.dumps({"error": kind}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return exit_code


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return EXIT_OK


def _empty_store():
    return {"next_id": 1, "tasks": []}


def _validate_store(data):
    if not isinstance(data, dict):
        raise BadStore()
    if isinstance(data.get("next_id"), bool) or not isinstance(data.get("next_id"), int):
        raise BadStore()
    if data["next_id"] < 1:
        raise BadStore()
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise BadStore()
    seen = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise BadStore()
        tid = task.get("id")
        if isinstance(tid, bool) or not isinstance(tid, int) or tid < 1:
            raise BadStore()
        if tid in seen:
            raise BadStore()
        seen.add(tid)
        if not isinstance(task.get("text"), str):
            raise BadStore()
        if not isinstance(task.get("done"), bool):
            raise BadStore()
        created = task.get("created_at")
        if isinstance(created, bool) or not isinstance(created, (int, float)):
            raise BadStore()
        expires = task.get("expires_at")
        if expires is not None and (
            isinstance(expires, bool) or not isinstance(expires, (int, float))
        ):
            raise BadStore()
        if tid >= data["next_id"]:
            raise BadStore()
    return data


def load_store(path):
    if not os.path.exists(path):
        return _empty_store()
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        raise BadStore()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise BadStore()
    return _validate_store(data)


def save_store(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def view_task(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": bool(task["done"]),
        "created_at": float(task["created_at"]),
        "expires_at": None if task["expires_at"] is None else float(task["expires_at"]),
    }


def is_expired(task, now):
    expires = task["expires_at"]
    return expires is not None and now >= expires


def classify(task, now):
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def cmd_add(store, args, now):
    text = args.text
    if text.strip() == "":
        raise BadRequest()
    ttl = args.ttl
    if ttl is not None and not ttl > 0:
        raise BadRequest()
    task = {
        "id": store["next_id"],
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": None if ttl is None else float(now) + float(ttl),
    }
    store["next_id"] += 1
    store["tasks"].append(task)
    return {"task": view_task(task)}


def cmd_list(store, args, now):
    status = args.status
    tasks = sorted(store["tasks"], key=lambda t: t["id"])
    if status == "all":
        selected = tasks
    else:
        selected = [t for t in tasks if classify(t, now) == status]
    return {"tasks": [view_task(t) for t in selected]}


def cmd_done(store, args, now):
    for task in store["tasks"]:
        if task["id"] == args.id:
            task["done"] = True
            return {"task": view_task(task)}
    raise KeyError(args.id)


def cmd_stats(store, args, now):
    counts = {"total": 0, "open": 0, "done": 0, "expired": 0}
    for task in store["tasks"]:
        counts["total"] += 1
        counts[classify(task, now)] += 1
    return counts


def cmd_expire(store, args, now):
    expired = sorted(t["id"] for t in store["tasks"] if is_expired(t, now))
    if expired:
        keep = [t for t in store["tasks"] if not is_expired(t, now)]
        store["tasks"] = keep
    return {"expired": expired}


def build_parser():
    parser = argparse.ArgumentParser(prog="tasksvc", add_help=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--now", type=float, default=None)
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add")
    p_add.add_argument("text")
    p_add.add_argument("--ttl", type=float, default=None)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", choices=["open", "done", "expired", "all"], default="open")

    p_done = sub.add_parser("done")
    p_done.add_argument("id")

    sub.add_parser("stats")
    sub.add_parser("expire")
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code == 0:
            return EXIT_OK
        return _error(EXIT_BAD_REQUEST, "bad_request")

    if args.command is None:
        return _error(EXIT_BAD_REQUEST, "bad_request")

    now = time.time() if args.now is None else float(args.now)

    if args.command == "done":
        try:
            task_id = int(args.id)
        except (TypeError, ValueError):
            return _error(EXIT_BAD_REQUEST, "bad_request")
    else:
        task_id = None

    handles = {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "stats": cmd_stats,
        "expire": cmd_expire,
    }
    handler = handles[args.command]

    try:
        store = load_store(args.db)
    except BadStore:
        return _error(EXIT_BAD_STORE, "bad_store")

    try:
        if task_id is not None:
            args.id = task_id
        elif args.command == "done":
            return _error(EXIT_BAD_REQUEST, "bad_request")
    except Exception:
        return _error(EXIT_BAD_REQUEST, "bad_request")

    try:
        payload = handler(store, args, now)
    except BadRequest:
        return _error(EXIT_BAD_REQUEST, "bad_request")
    except KeyError:
        return _error(EXIT_NOT_FOUND, "not_found")

    try:
        save_store(args.db, store)
    except BadStore:
        return _error(EXIT_BAD_STORE, "bad_store")

    return _emit(payload)


if __name__ == "__main__":
    sys.exit(main())
