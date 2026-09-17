"""业务层: 任务视图 / 过期判定 / 命令实现。

契约要点:
- 视图互斥, 过期优先于 done:
    open    = 未 done 且未过期
    done    = 已 done 且未过期
    expired = 已过期 (无论 done 与否)
    all     = 全部
- 过期判定: now >= expires_at 即为已过期 (边界含等号)。
- 列表一律按 id 升序。
- done 幂等: 已 done 再 done 仍成功。
- expire: 真删除已过期任务, 返回被删 id 升序列表。
- id 单调永不复用: 分配用 next_id 并自增, 删除不回退。
"""


class NotFound(Exception):
    """未知 id。"""


class BadRequest(Exception):
    """参数/用法错误。"""


def _is_expired(task, now):
    if now is None:
        return False
    exp = task.get("expires_at")
    return exp is not None and now >= exp


def is_expired(task, now):
    return _is_expired(task, now)


def _view(task, status, now):
    expired = _is_expired(task, now)
    if status == "expired":
        return expired
    if status == "all":
        return True
    if status == "done":
        return task["done"] and not expired
    # open
    return (not task["done"]) and (not expired)


def _dump(task):
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": task["created_at"],
        "expires_at": task["expires_at"],
    }


def _find(data, tid):
    for t in data["tasks"]:
        if t["id"] == tid:
            return t
    return None


def cmd_add(data, text, ttl, now):
    if text.strip() == "":
        raise BadRequest("empty text")
    if ttl is not None and ttl <= 0:
        raise BadRequest("ttl must be > 0")
    tid = data["next_id"]
    data["next_id"] = tid + 1
    task = {
        "id": tid,
        "text": text,
        "done": False,
        "created_at": now,
        "expires_at": (now + ttl) if ttl is not None else None,
    }
    data["tasks"].append(task)
    return {"task": _dump(task)}


def cmd_list(data, status, now):
    tasks = sorted((t for t in data["tasks"] if _view(t, status, now)),
                   key=lambda t: t["id"])
    return {"tasks": [_dump(t) for t in tasks]}


def cmd_done(data, tid, now):
    task = _find(data, tid)
    if task is None:
        raise NotFound(tid)
    task["done"] = True  # 幂等
    return {"task": _dump(task)}


def cmd_stats(data, now):
    total = len(data["tasks"])
    expired = sum(1 for t in data["tasks"] if _is_expired(t, now))
    done = sum(1 for t in data["tasks"]
               if t["done"] and not _is_expired(t, now))
    opn = sum(1 for t in data["tasks"]
              if (not t["done"]) and (not _is_expired(t, now)))
    return {"total": total, "open": opn, "done": done, "expired": expired}


def cmd_expire(data, now):
    if now is None:
        return {"expired": []}
    kept = []
    removed = []
    for t in data["tasks"]:
        if _is_expired(t, now):
            removed.append(t["id"])
        else:
            kept.append(t)
    data["tasks"] = kept
    return {"expired": sorted(removed)}
