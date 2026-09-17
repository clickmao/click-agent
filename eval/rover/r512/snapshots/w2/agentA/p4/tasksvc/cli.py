"""tasksvc.cli -- task-queue CLI (Python 3 stdlib only, no network).

Run:
    python3 -B -m tasksvc.cli --db <path> --now <epoch> <command> [args]

Contract highlights
-------------------
* Global options ``--db <path>`` and ``--now <epoch>`` come BEFORE the
  subcommand.  ``--now`` injects the clock (int/float epoch seconds); no
  ``sleep`` is ever used and no other time source is consulted.
* Every invocation prints exactly ONE JSON object to stdout
  (``ensure_ascii=False``, at most one trailing newline) and nothing else.
* Storage is a single JSON file:
      {"next_id": int, "tasks": [task, ...]}
  with ``next_id`` persisted and monotonically non-decreasing (ids are never
  reused, even after delete/expire).
* Writes are atomic: temp file in the same directory + ``os.replace``; no
  temp residue, and readers always see a complete JSON document.
* Views: open = not done AND not expired; done = done; expired = expired;
  expired takes precedence over done (mutually exclusive); ``all`` = every
  stored task.  Lists are always sorted ascending by id.
* Expiry: ``--ttl N`` sets ``expires_at = now + N``; ``now >= expires_at``
  means expired.  ``expire`` really deletes the expired rows.
* Exit codes: 0 ok; 2 bad_request (blank text, non-int id, ttl <= 0,
  unknown command); 3 not_found (unknown id); 4 bad_store (corrupt file).
* Exit code 1 is written as an ``{"error":"internal"}`` path only for
  genuinely unexpected IO/OS failures.

Self-test:
    python3 -B -m tasksvc.cli --selftest
    -> prints PASS/FAIL to stdout, exit code 0 on pass, 1 on fail.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4

USAGE = (
    "usage: python3 -B -m tasksvc.cli --db <path> --now <epoch> "
    "<add|list|done|stats|expire> [args]\n"
)


# --------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------
def emit(obj: Dict[str, Any]) -> None:
    """Print exactly one JSON object plus an optional trailing newline."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


class BadStore(Exception):
    """Raised when the backing file is not valid JSON or fails schema."""


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def load_store(path: str) -> Dict[str, Any]:
    """Load and validate the store; absent file -> fresh store."""
    if not os.path.exists(path):
        return {"next_id": 1, "tasks": []}
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        raise BadStore("unreadable")
    # UTF-8 strictly (BOM is not acceptable JSON either).
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BadStore("not utf-8")
    try:
        data = json.loads(text)
    except (ValueError, UnicodeDecodeError):
        raise BadStore("not json")
    if not isinstance(data, dict):
        raise BadStore("root not object")
    if "next_id" not in data or not isinstance(data["next_id"], int) \
            or isinstance(data["next_id"], bool):
        raise BadStore("next_id")
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise BadStore("tasks")
    for row in data["tasks"]:
        if not isinstance(row, dict):
            raise BadStore("task not object")
        if not isinstance(row.get("id"), int) or isinstance(row.get("id"), bool):
            raise BadStore("task.id")
        if not isinstance(row.get("text"), str):
            raise BadStore("task.text")
        if not isinstance(row.get("done"), bool):
            raise BadStore("task.done")
        if not isinstance(row.get("created_at"), (int, float)) \
                or isinstance(row.get("created_at"), bool):
            raise BadStore("task.created_at")
        exp = row.get("expires_at")
        if exp is not None and (not isinstance(exp, (int, float))
                                or isinstance(exp, bool)):
            raise BadStore("task.expires_at")
    return data


def save_store(path: str, data: Dict[str, Any]) -> None:
    """Atomically write the store: same-dir temp file + os.replace."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# domain
# --------------------------------------------------------------------------
def is_expired(task: Dict[str, Any], now: float) -> bool:
    exp = task.get("expires_at")
    return exp is not None and now >= exp


def view_of(task: Dict[str, Any], now: float) -> str:
    """Mutually exclusive view; expiry wins over done."""
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def public_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Project a stored task onto the exact public schema."""
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


# --------------------------------------------------------------------------
# argument parsing (hand-rolled: options may appear before/after positionals,
# but the global --db/--now MUST precede the subcommand)
# --------------------------------------------------------------------------
class BadRequest(Exception):
    pass


def parse_ttl(value: str) -> float:
    try:
        ttl = float(value)
    except (TypeError, ValueError):
        raise BadRequest("ttl")
    if ttl != ttl or ttl in (float("inf"), float("-inf")):  # NaN/inf
        raise BadRequest("ttl")
    if ttl <= 0:
        raise BadRequest("ttl")
    return ttl


def parse_id(value: str) -> int:
    s = value.strip()
    body = s[1:] if s[:1] in ("+", "-") else s
    if not body or not body.isdigit():
        raise BadRequest("id")
    return int(s)


def parse_now(value: str) -> float:
    try:
        now = float(value)
    except (TypeError, ValueError):
        raise BadRequest("now")
    if now != now:
        raise BadRequest("now")
    return now


def split_globals(argv: List[str]) -> Tuple[Optional[str], Optional[float], List[str]]:
    """Consume leading --db/--now; the rest starts at the subcommand."""
    db: Optional[str] = None
    now: Optional[float] = None
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--db" and i + 1 < len(argv):
            db = argv[i + 1]
            i += 2
        elif tok.startswith("--db="):
            db = tok[len("--db="):]
            i += 1
        elif tok == "--now" and i + 1 < len(argv):
            now = parse_now(argv[i + 1])
            i += 2
        elif tok.startswith("--now="):
            now = parse_now(tok[len("--now="):])
            i += 1
        else:
            break
    return db, now, argv[i:]


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_add(store: Dict[str, Any], now: float, args: List[str]) -> int:
    text: Optional[str] = None
    ttl: Optional[float] = None
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--ttl":
            if i + 1 >= len(args):
                raise BadRequest("ttl")
            ttl = parse_ttl(args[i + 1])
            i += 2
        elif tok.startswith("--ttl="):
            ttl = parse_ttl(tok[len("--ttl="):])
            i += 1
        else:
            if text is None:
                text = tok
            else:
                # extra positional: fold with a single space so that the
                # bytestring intent of a quoted argument is preserved.
                text = text + " " + tok
            i += 1
    if text is None or text.strip() == "":
        raise BadRequest("text")
    task = {
        "id": store["next_id"],
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": (now + ttl) if ttl is not None else None,
    }
    store["next_id"] = store["next_id"] + 1
    store["tasks"].append(task)
    save_store(STATE["db"], store)
    emit({"task": public_task(task)})
    return EXIT_OK


def cmd_list(store: Dict[str, Any], now: float, args: List[str]) -> int:
    status = "open"
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--status":
            if i + 1 >= len(args):
                raise BadRequest("status")
            status = args[i + 1]
            i += 2
        elif tok.startswith("--status="):
            status = tok[len("--status="):]
            i += 1
        else:
            raise BadRequest("list")
    if status not in ("open", "done", "expired", "all"):
        raise BadRequest("status")
    rows = []
    for task in sorted(store["tasks"], key=lambda t: t["id"]):
        if status == "all" or view_of(task, now) == status:
            rows.append(public_task(task))
    emit({"tasks": rows})
    return EXIT_OK


def cmd_done(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if len(args) != 1:
        raise BadRequest("done")
    task_id = parse_id(args[0])
    for task in store["tasks"]:
        if task["id"] == task_id:
            if not task["done"]:
                task["done"] = True
                save_store(STATE["db"], store)
            emit({"task": public_task(task)})  # idempotent
            return EXIT_OK
    emit_not_found()
    return EXIT_NOT_FOUND


def cmd_stats(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if args:
        raise BadRequest("stats")
    counts = {"total": 0, "open": 0, "done": 0, "expired": 0}
    for task in store["tasks"]:
        counts["total"] += 1
        counts[view_of(task, now)] += 1
    emit({"total": counts["total"], "open": counts["open"],
          "done": counts["done"], "expired": counts["expired"]})
    return EXIT_OK


def cmd_expire(store: Dict[str, Any], now: float, args: List[str]) -> int:
    if args:
        raise BadRequest("expire")
    kept: List[Dict[str, Any]] = []
    removed: List[int] = []
    for task in store["tasks"]:
        if is_expired(task, now):
            removed.append(task["id"])
        else:
            kept.append(task)
    if removed:
        store["tasks"] = kept
        save_store(STATE["db"], store)
    removed.sort()
    emit({"expired": removed})
    return EXIT_OK


def emit_not_found() -> None:
    emit({"error": "not_found"})


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "stats": cmd_stats,
    "expire": cmd_expire,
}

# Shared runtime state so command handlers can persist without threading the
# path through every call site.
STATE: Dict[str, str] = {"db": ""}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def run(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        sys.stderr.write(USAGE)
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    db, now, rest = split_globals(argv)
    if db is None or now is None or not rest:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    command = rest[0]
    handler = COMMANDS.get(command)
    if handler is None:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST

    STATE["db"] = db
    try:
        store = load_store(db)
    except BadStore:
        emit({"error": "bad_store"})
        return EXIT_BAD_STORE

    try:
        return handler(store, now, rest[1:])
    except BadRequest:
        emit({"error": "bad_request"})
        return EXIT_BAD_REQUEST
    except OSError:
        emit({"error": "internal"})
        return EXIT_INTERNAL


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "--selftest":
        sys.exit(selftest())
    sys.exit(run(argv))


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def selftest() -> int:
    """Headless end-to-end self-check over the real CLI surface.

    Drives ``run()`` (the production entry) for every scenario so the tests
    observe exactly what an external caller observes.  Prints PASS/FAIL.
    """
    import contextlib
    import io

    failures: List[str] = []

    def call(args: List[str]) -> Tuple[int, Any]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run(args)
        out = buf.getvalue()
        try:
            obj = json.loads(out)
        except ValueError:
            failures.append("non-json output for %r: %r" % (args, out))
            return rc, None
        if out.count("\n") > 1 or (out != "\n" and not out.endswith("\n")):
            failures.append("bad framing for %r: %r" % (args, out))
        return rc, obj

    tmpdir = tempfile.mkdtemp(prefix="tasksvc-selftest-")
    db = os.path.join(tmpdir, "store.json")

    try:
        # --- empty store -------------------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "list"])
        if (rc, obj) != (0, {"tasks": []}):
            failures.append("empty list: %r %r" % (rc, obj))

        # --- add: text round-trip incl. emoji/leading+trailing spaces ----
        text = "  \u4efb\u52a1 \U0001F680  "
        rc, obj = call(["--db", db, "--now", "100", "add", text])
        if rc != 0 or obj["task"]["text"] != text:
            failures.append("text round-trip: %r %r" % (rc, obj))
        if obj["task"]["id"] != 1 or obj["task"]["done"] is not False:
            failures.append("add defaults: %r" % (obj,))
        if obj["task"]["created_at"] != 100.0 or obj["task"]["expires_at"] is not None:
            failures.append("add times: %r" % (obj,))

        # --- add with ttl -------------------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "add", "with-ttl", "--ttl", "50"])
        if rc != 0 or obj["task"]["expires_at"] != 150.0:
            failures.append("ttl add: %r %r" % (rc, obj))

        # --- blank text -> bad_request ------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "add", "   "])
        if (rc, obj) != (2, {"error": "bad_request"}):
            failures.append("blank text: %r %r" % (rc, obj))

        # --- ttl <= 0 -> bad_request --------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "add", "x", "--ttl", "0"])
        if (rc, obj) != (2, {"error": "bad_request"}):
            failures.append("ttl zero: %r %r" % (rc, obj))

        # --- unknown command ----------------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "frobnicate"])
        if (rc, obj) != (2, {"error": "bad_request"}):
            failures.append("unknown cmd: %r %r" % (rc, obj))

        # --- non-int id -> bad_request ------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "done", "abc"])
        if (rc, obj) != (2, {"error": "bad_request"}):
            failures.append("non-int id: %r %r" % (rc, obj))

        # --- unknown id -> not_found --------------------------------------
        rc, obj = call(["--db", db, "--now", "100", "done", "999"])
        if (rc, obj) != (3, {"error": "not_found"}):
            failures.append("unknown id: %r %r" % (rc, obj))

        # --- done idempotent ----------------------------------------------
        rc, obj = call(["--db", db, "--now", "101", "done", "1"])
        if rc != 0 or obj["task"]["done"] is not True:
            failures.append("done#1: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "102", "done", "1"])
        if rc != 0 or obj["task"]["done"] is not True or obj["task"]["id"] != 1:
            failures.append("done#2 idempotent: %r %r" % (rc, obj))

        # --- expiry boundary: now == expires_at is expired ---------------
        # task 2 expires at 150 exactly.
        rc, obj = call(["--db", db, "--now", "149", "list", "--status", "open"])
        if rc != 0 or [t["id"] for t in obj["tasks"]] != [2]:
            failures.append("open just before expiry: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "150", "list", "--status", "open"])
        if rc != 0 or obj["tasks"] != []:
            failures.append("open at exact expiry: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "150", "list", "--status", "expired"])
        if rc != 0 or [t["id"] for t in obj["tasks"]] != [2]:
            failures.append("expired view: %r %r" % (rc, obj))

        # --- expiry beats done (mutually exclusive) -----------------------
        # mark 2 done while already expired; still only in expired view.
        rc, obj = call(["--db", db, "--now", "160", "done", "2"])
        if rc != 0 or obj["task"]["done"] is not True:
            failures.append("done on expired: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "160", "list", "--status", "done"])
        if rc != 0 or [t["id"] for t in obj["tasks"]] != [1]:
            failures.append("done view excludes expired: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "160", "list", "--status", "expired"])
        if rc != 0 or [t["id"] for t in obj["tasks"]] != [2]:
            failures.append("expired view incl. done+expired: %r %r" % (rc, obj))

        # --- stats ---------------------------------------------------------
        rc, obj = call(["--db", db, "--now", "160", "stats"])
        if (rc, obj) != (0, {"total": 2, "open": 0, "done": 1, "expired": 1}):
            failures.append("stats: %r %r" % (rc, obj))

        # --- expire really deletes + ids never reused ---------------------
        rc, obj = call(["--db", db, "--now", "160", "expire"])
        if (rc, obj) != (0, {"expired": [2]}):
            failures.append("expire: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "160", "stats"])
        if (rc, obj) != (0, {"total": 1, "open": 0, "done": 1, "expired": 0}):
            failures.append("post-expire stats: %r %r" % (rc, obj))
        rc, obj = call(["--db", db, "--now", "160", "add", "new"])
        if rc != 0 or obj["task"]["id"] != 3:
            failures.append("id monotonic after expire: %r %r" % (rc, obj))

        # --- next_id persisted across process invocations -----------------
        with open(db, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if raw["next_id"] != 4:
            failures.append("next_id persisted: %r" % (raw.get("next_id"),))
        if os.path.getsize(db) == 0:
            failures.append("store empty")

        # --- corrupt store -> bad_store -----------------------------------
        bad = os.path.join(tmpdir, "bad.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        rc, obj = call(["--db", bad, "--now", "1", "list"])
        if (rc, obj) != (4, {"error": "bad_store"}):
            failures.append("bad json store: %r %r" % (rc, obj))

        schema_bad = os.path.join(tmpdir, "schema.json")
        with open(schema_bad, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"tasks": []}))  # missing next_id
        rc, obj = call(["--db", schema_bad, "--now", "1", "list"])
        if (rc, obj) != (4, {"error": "bad_store"}):
            failures.append("bad schema store: %r %r" % (rc, obj))

        # --- missing global flags ------------------------------------------
        rc, obj = call(["list"])
        if (rc, obj) != (2, {"error": "bad_request"}):
            failures.append("missing globals: %r %r" % (rc, obj))

        # --- atomic write: no temp residue ---------------------------------
        residue = [n for n in os.listdir(tmpdir) if n.startswith(".tasksvc-")]
        if residue:
            failures.append("temp residue: %r" % (residue,))

        # --- negative control: a deliberately broken assertion must fail ---
        rc, obj = call(["--db", db, "--now", "160", "list", "--status", "all"])
        # 'all' must include every stored task (id 1 and id 3).
        if [t["id"] for t in obj["tasks"]] != [1, 3]:
            failures.append("all view: %r %r" % (rc, obj))

    finally:
        for name in os.listdir(tmpdir):
            try:
                os.unlink(os.path.join(tmpdir, name))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    if failures:
        sys.stdout.write("FAIL\n")
        for msg in failures:
            sys.stdout.write("  - %s\n" % msg)
        return 1
    sys.stdout.write("PASS\n")
    return 0


if __name__ == "__main__":
    main()
