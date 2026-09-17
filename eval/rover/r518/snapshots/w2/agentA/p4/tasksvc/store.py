"""存储层: JSON 文件的原子读写与 schema 校验。

文件形态 (合法 JSON 对象):
    {"next_id": int >= 1, "tasks": [TASKS...]}

task 记录:
    {"id": int, "text": str, "done": bool,
     "created_at": float|int, "expires_at": float|int|null}

设计约束:
- next_id 持久化、只增不减; 已删除/已过期的 id 不得复用。
- 写入必须原子: 写同目录临时文件 -> os.replace 重命名, 不留残留。
- 任何时刻读到的文件都是完整 JSON (UTF-8, 无 BOM)。
"""

import json
import os
import tempfile


class BadStore(Exception):
    """存储文件损坏: 非 JSON 或 schema 不符。"""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validate_task(t):
    if not isinstance(t, dict):
        raise BadStore("task not object")
    if not isinstance(t.get("id"), int) or isinstance(t["id"], bool):
        raise BadStore("id not int")
    if not isinstance(t.get("text"), str):
        raise BadStore("text not str")
    if not isinstance(t.get("done"), bool):
        raise BadStore("done not bool")
    if not _is_num(t.get("created_at")):
        raise BadStore("created_at not number")
    exp = t.get("expires_at")
    if exp is not None and not _is_num(exp):
        raise BadStore("expires_at not number/null")


def _validate(data):
    if not isinstance(data, dict):
        raise BadStore("root not object")
    nid = data.get("next_id")
    if not isinstance(nid, int) or isinstance(nid, bool) or nid < 1:
        raise BadStore("next_id not positive int")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise BadStore("tasks not list")
    for t in tasks:
        _validate_task(t)


def load(path):
    """读取并校验存储; 文件不存在返回初始态。损坏抛 BadStore。"""
    if not os.path.exists(path):
        return {"next_id": 1, "tasks": []}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, UnicodeDecodeError) as exc:
        raise BadStore(str(exc))
    except OSError as exc:
        raise BadStore(str(exc))
    _validate(data)
    return data


def save(path, data):
    """原子写回: 同目录临时文件 + os.replace, 失败时清理临时文件。"""
    _validate(data)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, sort_keys=True)
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
