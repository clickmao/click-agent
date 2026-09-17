"""Task domain logic: views, expiry, and formatting."""

from .store import BadStoreError


def is_expired(task, now):
    expires = task.get("expires_at")
    if expires is None:
        return False
    return now >= expires


def status_of(task, now):
    if is_expired(task, now):
        return "expired"
    if task.get("done"):
        return "done"
    return "open"


def public(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": bool(task["done"]),
        "created_at": float(task["created_at"]),
        "expires_at": None if task.get("expires_at") is None else float(task["expires_at"]),
    }


def select(data, status, now):
    tasks = sorted(data.get("tasks", []), key=lambda item: item["id"])
    if status == "all":
        return tasks
    return [task for task in tasks if status_of(task, now) == status]


def purge_expired(data, now):
    """Remove expired tasks in place, returning their ids in id order."""
    expired = [task for task in sorted(data["tasks"], key=lambda item: item["id"]) if is_expired(task, now)]
    expired_ids = [task["id"] for task in expired]
    if expired_ids:
        remove = set(expired_ids)
        data["tasks"] = [task for task in data["tasks"] if task["id"] not in remove]
    return expired_ids
