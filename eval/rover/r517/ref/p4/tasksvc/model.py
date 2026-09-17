"""领域层: 任务构造 / 校验 / 过期判定 / 视图 (open|done|expired|all)。"""
from __future__ import annotations

STATUSES = ("open", "done", "expired", "all")


class BadInput(Exception):
    """参数不符合契约 (退出码 2)。"""


def normalize_text(raw):
    """文本规范化: 必须存在, 去首尾空白后非空。内容本身逐字节保留。"""
    if raw is None:
        raise BadInput("text_required")
    if not isinstance(raw, str):
        raise BadInput("text_not_string")
    if raw.strip() == "":
        raise BadInput("text_blank")
    return raw


def parse_ttl(raw):
    """--ttl 必须是 > 0 的整数秒; 省略 = 永不过期。"""
    if raw is None:
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError) as exc:
        raise BadInput("ttl_not_int") from exc
    if v <= 0:
        raise BadInput("ttl_not_positive")
    return v


def parse_id(raw):
    """子命令里的 id 必须是十进制整数 (非整数 = bad_request, 不是 not_found)。"""
    try:
        v = int(raw)
    except (TypeError, ValueError) as exc:
        raise BadInput("id_not_int") from exc
    return v


def make_task(task_id, text, now, ttl):
    return {
        "id": task_id,
        "text": text,
        "done": False,
        "created_at": float(now),
        "expires_at": None if ttl is None else float(now) + float(ttl),
    }


def is_expired(task, now):
    """到期时刻起即视为过期 (now >= expires_at)。"""
    exp = task.get("expires_at")
    return exp is not None and float(now) >= float(exp)


def status_of(task, now):
    if is_expired(task, now):
        return "expired"
    return "done" if task.get("done") else "open"


def view(tasks, now, status="open"):
    """按 status 过滤后按 id 升序返回 (不修改入参)。"""
    if status not in STATUSES:
        raise BadInput("bad_status")
    if status == "all":
        picked = list(tasks)
    else:
        picked = [t for t in tasks if status_of(t, now) == status]
    return sorted(picked, key=lambda t: int(t["id"]))
