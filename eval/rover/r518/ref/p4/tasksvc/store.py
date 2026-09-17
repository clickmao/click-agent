"""JSON 存储层: 原子重写 (temp + fsync + rename), id 单调不复用。

契约 (与 prompt 第 4 条一致):
  · 文件形态: {"schema":1,"next_id":<int>,"tasks":[<task>, ...]}
  · 写入必须原子: 任何时刻读到的文件都是**完整 JSON**; 不留临时文件残留。
  · id 单调: next_id 只增不减, 已删除/已过期的 id 不复用。
"""
from __future__ import annotations

import json
import os
import tempfile

SCHEMA = 1


def default_state():
    return {"schema": SCHEMA, "next_id": 1, "tasks": []}


def load(path):
    """读状态; 文件不存在 = 空状态; 文件损坏抛 StoreError。"""
    if not os.path.exists(path):
        return default_state()
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    if not raw.strip():
        return default_state()
    try:
        st = json.loads(raw)
    except ValueError as exc:
        raise StoreError("bad_store") from exc
    if (
        not isinstance(st, dict)
        or st.get("schema") != SCHEMA
        or not isinstance(st.get("tasks"), list)
        or not isinstance(st.get("next_id"), int)
    ):
        raise StoreError("bad_store")
    return st


def save(path, state):
    """原子写: 同目录临时文件 → fsync → os.replace。"""
    path = os.path.abspath(path)
    d = os.path.dirname(path) or "."
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasksvc-tmp-", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(state, fh, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


class StoreError(Exception):
    """存储文件不可用 (schema 不符 / 非法 JSON)。"""

    def __init__(self, code):
        super().__init__(code)
        self.code = code
