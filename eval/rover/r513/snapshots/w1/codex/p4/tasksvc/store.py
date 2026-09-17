"""JSON-file backed task store with atomic writes."""

import json
import os
import tempfile


class BadStore(Exception):
    """Raised when the store file is not valid JSON or violates the schema."""


EMPTY_STORE = {"next_id": 1, "tasks": []}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate(data):
    if not isinstance(data, dict):
        raise BadStore("store root must be an object")
    if not _is_int(data.get("next_id")) or data["next_id"] < 1:
        raise BadStore("next_id must be a positive integer")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise BadStore("tasks must be a list")
    for task in tasks:
        if not isinstance(task, dict):
            raise BadStore("task must be an object")
        if not _is_int(task.get("id")) or task["id"] < 1:
            raise BadStore("task id must be a positive integer")
        if not isinstance(task.get("text"), str):
            raise BadStore("task text must be a string")
        if not isinstance(task.get("done"), bool):
            raise BadStore("task done must be a bool")
        if not _is_number(task.get("created_at")):
            raise BadStore("task created_at must be a number")
        expires_at = task.get("expires_at")
        if expires_at is not None and not _is_number(expires_at):
            raise BadStore("task expires_at must be a number or null")
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids):
        raise BadStore("task ids must be unique")
    if ids and max(ids) >= data["next_id"]:
        raise BadStore("next_id must exceed every existing task id")
    return data


def load(path):
    """Return the store dict, or a fresh empty store when the file is absent."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return dict(EMPTY_STORE, tasks=[])
    except OSError as exc:
        raise BadStore(str(exc))
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise BadStore(str(exc))
    return _validate(data)


def save(path, data):
    """Atomically write the store as UTF-8 (no BOM) JSON."""
    _validate(data)
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tasksvc-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)
