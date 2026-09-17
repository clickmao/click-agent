"""Atomic JSON storage for the task queue."""

from __future__ import annotations

import json
import os
import tempfile

STORE_VERSION = 1


class BadStore(Exception):
    """Raised when the store file is not valid JSON or has a bad schema."""


def _check_task(obj):
    if not isinstance(obj, dict):
        raise BadStore("task is not an object")
    if not isinstance(obj.get("id"), int) or isinstance(obj.get("id"), bool):
        raise BadStore("task id must be an int")
    if not isinstance(obj.get("text"), str):
        raise BadStore("task text must be a string")
    if not isinstance(obj.get("done"), bool):
        raise BadStore("task done must be a bool")
    if not isinstance(obj.get("created_at"), (int, float)) or isinstance(
        obj.get("created_at"), bool
    ):
        raise BadStore("task created_at must be a number")
    expires_at = obj.get("expires_at")
    if expires_at is not None and (
        not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool)
    ):
        raise BadStore("task expires_at must be a number or null")
    return {
        "id": obj["id"],
        "text": obj["text"],
        "done": obj["done"],
        "created_at": float(obj["created_at"]),
        "expires_at": None if expires_at is None else float(expires_at),
    }


def _check_store(doc):
    if not isinstance(doc, dict):
        raise BadStore("store root must be an object")
    next_id = doc.get("next_id")
    if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 1:
        raise BadStore("next_id must be a positive int")
    tasks_raw = doc.get("tasks", [])
    if not isinstance(tasks_raw, list):
        raise BadStore("tasks must be a list")
    tasks = [_check_task(t) for t in tasks_raw]
    ids = [t["id"] for t in tasks]
    if len(set(ids)) != len(ids):
        raise BadStore("duplicate task ids")
    if any(i >= next_id for i in ids):
        raise BadStore("task id must be less than next_id")
    tasks.sort(key=lambda t: t["id"])
    return {"next_id": next_id, "tasks": tasks}


def empty_store():
    return {"next_id": 1, "tasks": []}


def load(path):
    if not os.path.exists(path):
        return empty_store()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        raise BadStore("cannot read store file")
    if raw.strip() == "":
        raise BadStore("store file is empty")
    try:
        doc = json.loads(raw)
    except ValueError:
        raise BadStore("store file is not valid JSON")
    return _check_store(doc)


def save(path, store):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    payload = json.dumps(store, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
