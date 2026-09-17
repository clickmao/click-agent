"""Task lifecycle logic independent of the CLI layer."""

from . import store


class NotFound(Exception):
    """Raised when a referenced task id does not exist."""


def is_expired(task, now):
    expires_at = task.get("expires_at")
    return expires_at is not None and now >= expires_at


def status_of(task, now):
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def view(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


def add(data, text, now, ttl):
    task_id = data["next_id"]
    task = {
        "id": task_id,
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": None if ttl is None else now + ttl,
    }
    data["next_id"] = task_id + 1
    data["tasks"].append(task)
    return task


def find(data, task_id):
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise NotFound(task_id)


def mark_done(data, task_id, now):
    task = find(data, task_id)
    if is_expired(task, now):
        raise NotFound(task_id)
    task["done"] = True
    return task


def list_tasks(data, now, status):
    tasks = sorted(data["tasks"], key=lambda item: item["id"])
    if status == "all":
        return tasks
    return [task for task in tasks if status_of(task, now) == status]


def stats(data, now):
    counts = {"total": len(data["tasks"]), "open": 0, "done": 0, "expired": 0}
    for task in data["tasks"]:
        counts[status_of(task, now)] += 1
    return counts


def expire(data, now):
    expired = [task["id"] for task in data["tasks"] if is_expired(task, now)]
    expired.sort()
    if expired:
        dead = set(expired)
        data["tasks"] = [task for task in data["tasks"] if task["id"] not in dead]
    return expired
