"""Task queue CLI service (Python 3 standard library only).

Supports parallel-safe access to a JSON store via flock + atomic rename.
"""
from __future__ import annotations

import argparse
import errno
import json
import math
import os
import sys
import tempfile

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None

PROG = "tasksvc"
DEFAULT_DB = "tasks.json"

EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

ERR_BAD_REQUEST = "bad_request"
ERR_NOT_FOUND = "not_found"
ERR_BAD_STORE = "bad_store"


class UsageError(Exception):
    """Argument or usage error -> exit 2."""


class StoreError(Exception):
    """Store missing/corrupt or schema violation -> exit 4."""


class NotFoundError(Exception):
    """Unknown id -> exit 3."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D401 - argparse hook
        raise UsageError(message)


class JsonOut:
    def __init__(self):
        self.buf = []

    def set(self, obj):
        self.buf = [obj]

    def emit(self):
        if not self.buf:
            return
        obj = self.buf[0]
        if isinstance(obj, dict) and "error" in obj and len(obj) == 1:
            print(json.dumps(obj, ensure_ascii=False))
        else:
            print(json.dumps(obj, ensure_ascii=False))


def _coerce_float(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StoreError("non-numeric time")
    f = float(value)
    if math.isnan(f) or math.isinf(f):
        raise StoreError("non-finite time")
    return f


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------
class Store:
    """JSON store guarded by an exclusive lock on a sibling .lock file.

    Reads snapshot the file under a shared lock; writes are always performed
    as write-temp-then-atomic-rename while holding the exclusive lock.
    """

    def __init__(self, path):
        self.path = path
        self.lock_path = path + ".lock"
        self._lock_fd = None
        self._existing = None

    # -- locking -----------------------------------------------------------
    def acquire(self):
        if fcntl is None:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError:
            pass
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self._lock_fd = fd

    def release(self):
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None

    # -- raw IO ------------------------------------------------------------
    def _raw_read(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = fh.read()
        except FileNotFoundError:
            return None
        except IsADirectoryError:
            raise StoreError("db path is a directory")
        except OSError as exc:
            raise StoreError("cannot read db: %s" % exc)
        if data.strip() == "":
            raise StoreError("empty store")
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise StoreError("invalid JSON: %s" % exc)

    def load(self):
        raw = self._raw_read()
        if raw is None:
            state = {"next_id": 1, "tasks": []}
            self._existing = None
            return state
        if not isinstance(raw, dict):
            raise StoreError("store root must be an object")
        if "next_id" not in raw:
            raise StoreError("missing next_id")
        next_id = raw["next_id"]
        if isinstance(next_id, bool) or not isinstance(next_id, int):
            raise StoreError("next_id must be an integer")
        if next_id < 1:
            raise StoreError("next_id must be >= 1")
        tasks_raw = raw.get("tasks", [])
        if tasks_raw is None:
            tasks_raw = []
        if not isinstance(tasks_raw, list):
            raise StoreError("tasks must be a list")

        tasks = []
        seen_ids = set()
        for item in tasks_raw:
            task = self._validate_task(item)
            if task["id"] in seen_ids:
                raise StoreError("duplicate task id")
            seen_ids.add(task["id"])
            tasks.append(task)
        state = {"next_id": next_id, "tasks": tasks}
        self._existing = state
        return state

    @staticmethod
    def _validate_task(item):
        if not isinstance(item, dict):
            raise StoreError("task must be an object")
        for key in ("id", "text", "done", "created_at"):
            if key not in item:
                raise StoreError("task missing field: %s" % key)
        tid = item["id"]
        if isinstance(tid, bool) or not isinstance(tid, int):
            raise StoreError("task id must be an integer")
        if not isinstance(item["text"], str):
            raise StoreError("task text must be a string")
        if not isinstance(item["done"], bool):
            raise StoreError("task done must be a boolean")
        created_at = _coerce_float(item["created_at"])
        expires_raw = item.get("expires_at")
        if expires_raw is None:
            expires_at = None
        else:
            expires_at = _coerce_float(expires_raw)
        return {
            "id": tid,
            "text": item["text"],
            "done": item["done"],
            "created_at": created_at,
            "expires_at": expires_at,
        }

    def save(self, state):
        payload = json.dumps(
            {
                "next_id": state["next_id"],
                "tasks": [
                    {
                        "id": t["id"],
                        "text": t["text"],
                        "done": t["done"],
                        "created_at": t["created_at"],
                        "expires_at": t["expires_at"],
                    }
                    for t in state["tasks"]
                ],
            },
            ensure_ascii=False,
        )
        directory = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as exc:
            raise StoreError("cannot create db directory: %s" % exc)
        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                prefix=".tasksvc-", suffix=".tmp", dir=directory
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fd = None
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, self.path)
            tmp_path = None
        except OSError as exc:
            raise StoreError("cannot write db: %s" % exc)
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# --------------------------------------------------------------------------
# Time / status helpers
# --------------------------------------------------------------------------
def is_expired(task, now):
    exp = task["expires_at"]
    return exp is not None and now >= exp


def view_of(task, now):
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def sort_tasks(tasks):
    return sorted(tasks, key=lambda t: t["id"])


def task_view(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
USAGE = (
    "usage: tasksvc [-h] [--db PATH] [--now EPOCH] {add,list,done,stats,expire} ..."
)


def build_parser():
    parser = _Parser(prog=PROG, add_help=False, allow_abbrev=False)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--now", default=None)
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", add_help=False, allow_abbrev=False)
    p_add.add_argument("text")
    p_add.add_argument("--ttl", dest="ttl", default=None)
    p_add.add_argument("-h", "--help", action="store_true", dest="help")

    p_list = sub.add_parser("list", add_help=False, allow_abbrev=False)
    p_list.add_argument("--status", dest="status", default="open")
    p_list.add_argument("-h", "--help", action="store_true", dest="help")

    p_done = sub.add_parser("done", add_help=False, allow_abbrev=False)
    p_done.add_argument("id")
    p_done.add_argument("-h", "--help", action="store_true", dest="help")

    p_stats = sub.add_parser("stats", add_help=False, allow_abbrev=False)
    p_stats.add_argument("-h", "--help", action="store_true", dest="help")

    p_expire = sub.add_parser("expire", add_help=False, allow_abbrev=False)
    p_expire.add_argument("-h", "--help", action="store_true", dest="help")
    return parser


def parse_int(value, what):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise UsageError("%s must be an integer" % what)


def parse_now(value):
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise UsageError("--now must be a number")
    if math.isnan(f) or math.isinf(f):
        raise UsageError("--now must be finite")
    return f


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_add(store, state, now, args):
    if args.text.strip() == "":
        raise UsageError("text must not be blank")
    ttl_raw = args.ttl
    expires_at = None
    if ttl_raw is not None:
        ttl = parse_int(ttl_raw, "--ttl")
        if ttl <= 0:
            raise UsageError("--ttl must be positive")
        expires_at = float(now) + float(ttl)

    tid = state["next_id"]
    task = {
        "id": tid,
        "text": args.text,
        "done": False,
        "created_at": float(now),
        "expires_at": expires_at,
    }
    state["next_id"] = tid + 1
    state["tasks"].append(task)
    store.save(state)
    return {"task": task_view(task)}


def cmd_list(store, state, now, args):
    status = args.status
    if status not in ("open", "done", "expired", "all"):
        raise UsageError("unknown status: %s" % status)
    tasks = state["tasks"]
    if status == "all":
        chosen = list(tasks)
    else:
        chosen = [t for t in tasks if view_of(t, now) == status]
    return {"tasks": [task_view(t) for t in sort_tasks(chosen)]}


def cmd_done(store, state, now, args):
    tid = parse_int(args.id, "id")
    for task in state["tasks"]:
        if task["id"] == tid:
            if not task["done"]:
                task["done"] = True
                store.save(state)
            return {"task": task_view(task)}
    raise NotFoundError(tid)


def cmd_stats(store, state, now, args):
    counts = {"total": 0, "open": 0, "done": 0, "expired": 0}
    for task in state["tasks"]:
        counts["total"] += 1
        counts[view_of(task, now)] += 1
    return {
        "total": counts["total"],
        "open": counts["open"],
        "done": counts["done"],
        "expired": counts["expired"],
    }


def cmd_expire(store, state, now, args):
    expired = []
    remaining = []
    for task in state["tasks"]:
        if is_expired(task, now):
            expired.append(task["id"])
        else:
            remaining.append(task)
    expired.sort()
    if expired:
        state["tasks"] = remaining
        store.save(state)
    return {"expired": expired}


COMMANDS = {
    "add": (cmd_add, False),
    "list": (cmd_list, True),
    "done": (cmd_done, True),
    "stats": (cmd_stats, True),
    "expire": (cmd_expire, True),
}

USAGE_TEXT = (
    "usage: tasksvc [--db PATH] [--now EPOCH] {add,list,done,stats,expire} ..."
)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = JsonOut()
    store = None
    try:
        parser = build_parser()
        ns = parser.parse_args(argv)
        if getattr(ns, "help", False) or not getattr(ns, "command", None):
            raise UsageError("usage")
        now = parse_now(ns.now)
        if now is None:
            raise UsageError("--now is required")

        store = Store(ns.db)
        store.acquire()
        state = store.load()
        handler = COMMANDS[ns.command][0]
        result = handler(store, state, now, ns)
        out.set(result)
        out.emit()
        return EXIT_OK
    except UsageError:
        print(json.dumps({"error": ERR_BAD_REQUEST}, ensure_ascii=False))
        return EXIT_BAD_REQUEST
    except NotFoundError:
        print(json.dumps({"error": ERR_NOT_FOUND}, ensure_ascii=False))
        return EXIT_NOT_FOUND
    except StoreError:
        print(json.dumps({"error": ERR_BAD_STORE}, ensure_ascii=False))
        return EXIT_BAD_STORE
    except SystemExit:
        raise
    except BaseException:
        print(json.dumps({"error": ERR_BAD_REQUEST}, ensure_ascii=False))
        return EXIT_BAD_REQUEST
    finally:
        if store is not None:
            store.release()


if __name__ == "__main__":
    sys.exit(main())
