"""领域逻辑：过期判定与视图分类。

判据（契约逐条绑定）:
  - 过期: expires_at is not None and now >= expires_at
  - 视图互斥且过期优先于 done:
        expired if is_expired else (done if done else open)
"""


def is_expired(task, now):
    exp = task["expires_at"]
    return exp is not None and now >= exp


def view_of(task, now):
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def select(tasks, status, now):
    """按视图过滤，id 升序返回。"""
    ordered = sorted(tasks, key=lambda t: t["id"])
    if status == "all":
        return ordered
    return [t for t in ordered if view_of(t, now) == status]


def counts(tasks, now):
    total = len(tasks)
    open_n = done_n = expired_n = 0
    for t in tasks:
        v = view_of(t, now)
        if v == "expired":
            expired_n += 1
        elif v == "done":
            done_n += 1
        else:
            open_n += 1
    return {"total": total, "open": open_n, "done": done_n, "expired": expired_n}
