"""tasksvc 核心逻辑: 存储、时钟、视图与过期语义。

约定(与 CLI 契约一一对应):
- 存储为一个合法 JSON 对象, 至少包含整数 ``next_id`` (持久化、只增不减)。
- 所有时间判定只使用外部注入的 now(epoch 秒), 不做 sleep。
- 过期优先于 done: 视图 open/done/expired 互斥。
- 写入原子: 临时文件 + 同目录 os.replace 重命名。
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List, Optional


class BadStore(Exception):
    """存储文件损坏(非 JSON 或 schema 不符)。"""


def _is_int(value: Any) -> bool:
    # 注意: bool 是 int 的子类, 需显式排除。
    return isinstance(value, int) and not isinstance(value, bool)


def _empty_store() -> Dict[str, Any]:
    return {"next_id": 1, "tasks": []}


def load_store(path: str) -> Dict[str, Any]:
    """读取存储文件; 不存在则返回空库; 损坏则抛出 BadStore。"""
    if not os.path.exists(path):
        return _empty_store()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        raise BadStore(path)
    if raw.strip() == "":
        # 空文件视为损坏(而非空库), 以免静默丢数据。
        raise BadStore(path)
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise BadStore(path)
    if not isinstance(data, dict):
        raise BadStore(path)
    if not _is_int(data.get("next_id")) or data["next_id"] < 1:
        raise BadStore(path)
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise BadStore(path)
    seen = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise BadStore(path)
        tid = task.get("id")
        if not _is_int(tid) or tid < 1:
            raise BadStore(path)
        if tid in seen:
            raise BadStore(path)
        seen.add(tid)
        if not isinstance(task.get("text"), str):
            raise BadStore(path)
        if not isinstance(task.get("done"), bool):
            raise BadStore(path)
        if not isinstance(task.get("created_at"), (int, float)) or isinstance(task.get("created_at"), bool):
            raise BadStore(path)
        exp = task.get("expires_at", None)
        if exp is not None and (not isinstance(exp, (int, float)) or isinstance(exp, bool)):
            raise BadStore(path)
    return {"next_id": data["next_id"], "tasks": tasks}


def save_store(path: str, store: Dict[str, Any]) -> None:
    """原子写入: 同目录临时文件 -> fsync -> os.replace。"""
    data = {
        "next_id": store["next_id"],
        "tasks": store["tasks"],
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    # 目标目录可能尚不存在(首次写入)。
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        # 失败时清理临时文件, 不留残留。
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """对外输出的 task 形态: 固定字段与顺序。"""
    return {
        "id": task["id"],
        "text": task["text"],
        "done": task["done"],
        "created_at": float(task["created_at"]),
        "expires_at": None if task.get("expires_at") is None else float(task["expires_at"]),
    }


def is_expired(task: Dict[str, Any], now: float) -> bool:
    """now >= expires_at 即为已过期(过期优先于 done)。"""
    exp = task.get("expires_at")
    if exp is None:
        return False
    return now >= exp


def view_of(task: Dict[str, Any], now: float) -> str:
    """返回 'expired' | 'done' | 'open' —— 互斥且过期优先。"""
    if is_expired(task, now):
        return "expired"
    if task["done"]:
        return "done"
    return "open"


def sorted_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(tasks, key=lambda t: t["id"])


def select(tasks: List[Dict[str, Any]], status: str, now: float) -> List[Dict[str, Any]]:
    if status == "all":
        chosen = list(tasks)
    else:
        chosen = [t for t in tasks if view_of(t, now) == status]
    return sorted_tasks(chosen)


def find_by_id(tasks: List[Dict[str, Any]], tid: int) -> Optional[Dict[str, Any]]:
    for t in tasks:
        if t["id"] == tid:
            return t
    return None
