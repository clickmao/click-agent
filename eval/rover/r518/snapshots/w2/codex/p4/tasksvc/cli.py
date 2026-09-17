"""Task queue CLI service backed by a JSON store.

Run as: python3 -B -m tasksvc.cli --db <path> [--now <epoch>] <command> ...
Only the Python 3 standard library is used.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

STORE_VERSION = 1
EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

STATUS_CHOICES = ("open", "done", "expired", "all")


class BadRequest(Exception):
    """Raised for usage / argument errors."""


class NotFound(Exception):
    """Raised when a task id does not exist."""


class BadStore(Exception):
    """Raised when the store file is not valid JSON or has a bad schema."""


def _emit(payload):
    """Print exactly one JSON object to stdout."""
    text = json.dumps(payload, ensure_ascii=False)
    sys.stdout.write(text)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _normalize_task(raw):
    """Validate and normalize a single task mapping from the store."""
    if not isinstance(raw, dict):
        raise BadStore("task entry is not an object")
    task_id = raw.get("id")
    if isinstance(task_id, bool) or not isinstance(task_id, int) or task_id < 1:
        raise BadStore("task id must be a positive integer")
    text = raw.get("text")
    if not isinstance(text, str):
        raise BadStore("task text must be a string")
    done = raw.get("done")
    if not isinstance(done, bool):
        raise BadStore("task done must be a boolean")
    created_at = raw.get("created_at")
    if isinstance(created_at, bool) or not isinstance(created_at, (int, float)):
        raise BadStore("task created_at must be a number")
    expires_at = raw.get("expires_at")
    if expires_at is not None:
        if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
            raise BadStore("task expires_at must be a number or null")
    return {
        "id": int(task_id),
        "text": text,
        "done": bool(done),
        "created_at": float(created_at),
        "expires_at": None if expires_at is None else float(expires_at),
    }


def load_store(path):
    """Load and validate the JSON store, or return a fresh store if absent."""
    if not isinstance(path, str) or not path:
        raise BadRequest("missing --db")
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError:
        return {"version": STORE_VERSION, "next_id": 1, "tasks": []}
    except OSError as exc:
        raise BadStore("cannot read store: %s" % (exc,)) from exc

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BadStore("store is not valid utf-8") from exc
    if text.startswith("\ufeff"):
        raise BadStore("store must not contain a BOM")

    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise BadStore("store is not valid json") from exc
    if not isinstance(parsed, dict):
        raise BadStore("store root must be an object")

    next_id = parsed.get("next_id")
    if isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1:
        raise BadStore("next_id must be a positive integer")

    raw_tasks = parsed.get("tasks", [])
    if not isinstance(raw_tasks, list):
        raise BadStore("tasks must be a list")

    tasks = []
    seen = set()
    for entry in raw_tasks:
        task = _normalize_task(entry)
        if task["id"] in seen:
            raise BadStore("duplicate task id %d" % task["id"])
        seen.add(task["id"])
        tasks.append(task)

    for task in tasks:
        if task["id"] >= next_id:
            raise BadStore("next_id must exceed every existing task id")

    tasks.sort(key=lambda item: item["id"])
    return {"version": STORE_VERSION, "next_id": int(next_id), "tasks": tasks}


def save_store(path, store):
    """Atomically write the store as UTF-8 JSON (no BOM)."""
    payload = {
        "version": STORE_VERSION,
        "next_id": int(store["next_id"]),
        "tasks": sorted(store["tasks"], key=lambda item: item["id"]),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
        dir_fd = None
        try:
            dir_fd = os.open(directory, os.O_RDONLY)
            os.fsync(dir_fd)
        except OSError:
            pass
        finally:
            if dir_fd is not None:
                os.close(dir_fd)
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def is_expired(task, now):
    """expires_at is exclusive: now >= expires_at counts as expired."""
    expires_at = task["expires_at"]
    if expires_at is None:
        return False
    return now >= expires_at


def matches_status(task, status, now):
    expired = is_expired(task, now)
    if status == "all":
        return True
    if status == "expired":
        return expired
    if status == "done":
        return (not expired) and task["done"]
    if status == "open":
        return (not expired) and (not task["done"])
    raise BadRequest("unknown status %r" % (status,))


def public_task(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


def _parse_float_option(value, name):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise BadRequest("%s must be a number" % name) from exc
    return parsed


def _parse_int(value, name):
    # Reject floats, signs with whitespace, and non-integer strings.
    stripped = value.strip() if isinstance(value, str) else value
    if not isinstance(stripped, str):
        raise BadRequest("%s must be an integer" % name)
    if stripped.lstrip("+-").isdigit() is False or stripped in ("", "+", "-"):
        raise BadRequest("%s must be an integer" % name)
    return int(stripped)


def parse_global_args(argv):
    """Parse global options that must appear before the subcommand."""
    db_path = None
    now = None
    has_now = False
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--db":
            if index + 1 >= len(argv):
                raise BadRequest("--db requires a value")
            db_path = argv[index + 1]
            index += 2
            continue
        if token == "--now":
            if index + 1 >= len(argv):
                raise BadRequest("--now requires a value")
            now = _parse_float_option(argv[index + 1], "--now")
            has_now = True
            index += 2
            continue
        break
    if db_path is None:
        raise BadRequest("--db is required")
    if not has_now:
        now = time.time()
    return db_path, now, argv[index:]


def parse_subcommand(rest):
    if not rest:
        raise BadRequest("missing subcommand")
    command = rest[0]
    args = rest[1:]
    if command not in ("add", "list", "done", "stats", "expire"):
        raise BadRequest("unknown subcommand %r" % (command,))
    return command, args


def cmd_add(store, now, args):
    text = None
    ttl = None
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--ttl":
            if index + 1 >= len(args):
                raise BadRequest("--ttl requires a value")
            ttl = _parse_float_option(args[index + 1], "--ttl")
            index += 2
            continue
        if token.startswith("--"):
            raise BadRequest("unknown option %r" % (token,))
        if text is not None:
            raise BadRequest("unexpected extra argument %r" % (token,))
        text = token
        index += 1

    if text is None:
        raise BadRequest("add requires <text>")
    if not text.strip():
        raise BadRequest("text must not be blank")
    if ttl is not None and ttl <= 0:
        raise BadRequest("--ttl must be positive")

    task_id = int(store["next_id"])
    store["next_id"] = task_id + 1
    task = {
        "id": task_id,
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": None if ttl is None else float(now) + float(ttl),
    }
    store["tasks"].append(task)
    save_store(store["_path"], store)
    return {"task": public_task(task)}


def cmd_list(store, now, args):
    status = "open"
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--status":
            if index + 1 >= len(args):
                raise BadRequest("--status requires a value")
            status = args[index + 1]
            index += 2
            continue
        if token.startswith("--status="):
            status = token.split("=", 1)[1]
            index += 1
            continue
        raise BadRequest("unexpected argument %r" % (token,))
    if status not in STATUS_CHOICES:
        raise BadRequest("unknown status %r" % (status,))

    tasks = [
        public_task(task)
        for task in sorted(store["tasks"], key=lambda item: item["id"])
        if matches_status(task, status, now)
    ]
    return {"tasks": tasks}


def cmd_done(store, now, args):
    if len(args) != 1:
        raise BadRequest("done requires exactly one id")
    task_id = _parse_int(args[0], "id")
    for task in store["tasks"]:
        if task["id"] == task_id:
            if not task["done"]:
                task["done"] = True
                save_store(store["_path"], store)
            return {"task": public_task(task)}
    raise NotFound("id %d not found" % task_id)


def cmd_stats(store, now, args):
    if args:
        raise BadRequest("stats takes no arguments")
    total = 0
    open_count = 0
    done_count = 0
    expired_count = 0
    for task in store["tasks"]:
        total += 1
        expired = is_expired(task, now)
        if expired:
            expired_count += 1
        elif task["done"]:
            done_count += 1
        else:
            open_count += 1
    return {
        "total": total,
        "open": open_count,
        "done": done_count,
        "expired": expired_count,
    }


def cmd_expire(store, now, args):
    if args:
        raise BadRequest("expire takes no arguments")
    expired_ids = []
    kept = []
    for task in store["tasks"]:
        if is_expired(task, now):
            expired_ids.append(task["id"])
        else:
            kept.append(task)
    expired_ids.sort()
    if expired_ids:
        store["tasks"] = kept
        save_store(store["_path"], store)
    return {"expired": expired_ids}


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        db_path, now, rest = parse_global_args(list(argv))
        command, args = parse_subcommand(rest)
        store = load_store(db_path)
        store["_path"] = db_path
        handler = COMMANDS[command]
        result = handler(store, now, args)
        _emit(result)
        return EXIT_OK
    except BadRequest:
        _emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except NotFound:
        _emit({"error": "not_found"})
        return EXIT_NOT_FOUND
    except BadStore:
        _emit({"error": "bad_store"})
        return EXIT_BAD_STORE


if __name__ == "__main__":
    sys.exit(main())
