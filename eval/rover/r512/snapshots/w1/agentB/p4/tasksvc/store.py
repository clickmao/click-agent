"""存储层：JSON 文件读写，原子落盘。

文件形态（合法 JSON 对象）:
    {"next_id": int, "tasks": [ {"id":int,"text":str,"done":bool,
                                 "created_at":float,"expires_at":float|null}, ... ]}
next_id 持久化、只增不减（永不复用已分配/已删除 id）。
"""

import json
import os
import secrets

# 退出码 / 错误契约
EXIT_OK = 0
EXIT_BAD_REQUEST = 2
EXIT_NOT_FOUND = 3
EXIT_BAD_STORE = 4


class StoreError(Exception):
    """存储文件损坏或 schema 不符 -> 退出码 4。"""


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_task(t):
    if not isinstance(t, dict):
        raise StoreError("task not object")
    if not _is_int(t.get("id")):
        raise StoreError("task.id must be int")
    if not isinstance(t.get("text"), str):
        raise StoreError("task.text must be str")
    if not isinstance(t.get("done"), bool):
        raise StoreError("task.done must be bool")
    if not isinstance(t.get("created_at"), (int, float)) or isinstance(t.get("created_at"), bool):
        raise StoreError("task.created_at must be number")
    exp = t.get("expires_at", None)
    if exp is not None and (not isinstance(exp, (int, float)) or isinstance(exp, bool)):
        raise StoreError("task.expires_at must be number or null")
    return {
        "id": t["id"],
        "text": t["text"],
        "done": t["done"],
        "created_at": float(t["created_at"]),
        "expires_at": (None if exp is None else float(exp)),
    }


def load(path):
    """读取存储；文件不存在时返回空库（合法初始态）；损坏 -> StoreError。"""
    if not os.path.exists(path):
        return {"next_id": 1, "tasks": []}
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        obj = json.loads(raw)
    except Exception as exc:  # 非 JSON
        raise StoreError("not json: %s" % exc)
    if not isinstance(obj, dict):
        raise StoreError("root must be object")
    if not _is_int(obj.get("next_id")):
        raise StoreError("next_id must be int")
    tasks_raw = obj.get("tasks", [])
    if not isinstance(tasks_raw, list):
        raise StoreError("tasks must be list")
    return {"next_id": obj["next_id"], "tasks": [_check_task(t) for t in tasks_raw]}


def save(path, db):
    """原子写：同目录临时文件 + os.replace，失败时清理临时文件。

    用纯 os.open/os.write 实现（不依赖 tempfile），保证同目录原子重命名且无残留。
    """
    payload = {
        "next_id": db["next_id"],
        "tasks": sorted(db["tasks"], key=lambda t: t["id"]),
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = os.path.join(directory, ".tasksvc-%s.tmp" % secrets.token_hex(8))
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)  # 同目录原子重命名
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
