"""JSON-file backed task store with atomic writes."""

import json
import os
import tempfile

BAD_STORE = "bad_store"


class BadStoreError(Exception):
    """Raised when the store file is not a valid JSON object with the expected schema."""


def _default_data():
    return {"next_id": 1, "tasks": []}


def _validate(data):
    if not isinstance(data, dict):
        raise BadStoreError()
    if "next_id" not in data or not isinstance(data["next_id"], int) or isinstance(data["next_id"], bool):
        raise BadStoreError()
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise BadStoreError()
    for task in tasks:
        if not isinstance(task, dict):
            raise BadStoreError()
        if not isinstance(task.get("id"), int) or isinstance(task.get("id"), bool):
            raise BadStoreError()
        if not isinstance(task.get("text"), str):
            raise BadStoreError()
        if not isinstance(task.get("done"), bool):
            raise BadStoreError()
        if not isinstance(task.get("created_at"), (int, float)) or isinstance(task.get("created_at"), bool):
            raise BadStoreError()
        expires = task.get("expires_at")
        if expires is not None:
            if not isinstance(expires, (int, float)) or isinstance(expires, bool):
                raise BadStoreError()
    return data


def load(path):
    """Load the store, returning default data if the file does not exist."""
    if not os.path.exists(path):
        return _default_data()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        raise BadStoreError()
    try:
        data = json.loads(raw)
    except ValueError:
        raise BadStoreError()
    return _validate(data)


def save(path, data):
    """Atomically write the store: temp file in same dir + os.replace."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return data
