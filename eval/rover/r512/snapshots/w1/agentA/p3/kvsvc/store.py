"""KvStore: 线程安全、带 TTL、WAL 持久化的键值存储。

设计要点
--------
* 单把 ``threading.RLock`` 保护内存表 + 计数器 + WAL 追加; 所有写操作在锁内
  完成"校验 -> 序列化 -> 落盘 -> 变更内存"，再用条件变量唤醒 incr 等待者。
* 过期语义: 惰性清除。任何访问(get/delete/incr/put/计数)都会先清理该键;
  ``count`` 只统计当前未过期键，``expired`` 统计累计因过期被清除的键数。
* WAL 格式: 每行一个 JSON 对象(UTF-8)，必含 ``op``(put/delete/incr) 与 ``key``。
  重放时按行顺序重建; ``ts`` 为写入墙钟时刻，用于恢复剩余 TTL，已过期的键不复活。
* 时间源: 单调钟 ``time.monotonic()`` 计 TTL(抗系统时间跳变); 另外记录
  ``time.time()`` 写入 WAL，重放时用 ``time.time()`` 还原绝对到期时刻。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class NotIntError(Exception):
    """incr 目标值存在且不是整数时抛出(映射为 HTTP 409)。"""


# 内部条目: (value, expire_at_monotonic_or_None)
_Entry = Tuple[Any, Optional[float]]


class KvStore:
    """线程安全的键值存储。

    参数:
        wal_path: WAL 文件路径; 若已存在则启动时重放恢复。
        clock:    单调钟(默认 ``time.monotonic``)，测试可注入。
        wall:     墙钟(默认 ``time.time``)，用于 WAL 里的绝对时间戳。
    """

    def __init__(
        self,
        wal_path: Optional[str] = None,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, _Entry] = {}
        self._expired = 0
        self._wal_path = os.path.abspath(wal_path) if wal_path else None
        self._clock = clock
        self._wall = wall
        self._t0 = clock()
        if self._wal_path:
            self._replay()

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _now(self) -> float:
        return self._clock()

    def _live(self, key: str) -> Optional[_Entry]:
        """返回未过期条目; 不存在或已过期时清理并计 expired, 返回 None。

        调用方必须已持有 ``self._lock``。
        """
        entry = self._data.get(key)
        if entry is None:
            return None
        _, expire_at = entry
        if expire_at is not None and self._now() >= expire_at:
            del self._data[key]
            self._expired += 1
            return None
        return entry

    def _append_wal(self, record: dict) -> None:
        """追加一行 JSON 到 WAL。调用方必须已持有 ``self._lock``。

        先序列化再写盘: 序列化失败(不可 JSON 化的 value)会抛错且不写盘,
        内存变更由调用方在成功返回后再执行, 保证 WAL 与内存一致。
        """
        if not self._wal_path:
            return
        line = json.dumps(record, ensure_ascii=False)
        with open(self._wal_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()

    def _replay(self) -> None:
        """启动时从 WAL 重放。

        已过期的键不复活; 重放本身不计入 ``expired``(该计数只统计运行期惰性清除)。
        """
        now_wall = self._wall()
        try:
            with open(self._wal_path, "r", encoding="utf-8-sig") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue  # 容忍被截断的尾行
                    if not isinstance(rec, dict):
                        continue
                    op = rec.get("op")
                    key = rec.get("key")
                    if not isinstance(key, str):
                        continue
                    if op == "put":
                        self._replay_put(rec, key, now_wall)
                    elif op == "delete":
                        self._data.pop(key, None)
                    elif op == "incr":
                        self._replay_incr(rec, key)
        except FileNotFoundError:
            pass

    def _replay_put(self, rec: dict, key: str, now_wall: float) -> None:
        ts = rec.get("ts", now_wall)
        ttl = rec.get("ttl")
        expire_at: Optional[float] = None
        if isinstance(ttl, (int, float)) and not isinstance(ttl, bool):
            deadline_wall = ts + float(ttl)
            if deadline_wall <= now_wall:
                self._data.pop(key, None)  # 已过期, 不复活
                return
            expire_at = self._now() + (deadline_wall - now_wall)
        self._data[key] = (rec.get("value"), expire_at)

    def _replay_incr(self, rec: dict, key: str) -> None:
        """重放 incr: 保留既有 TTL，在旧值基础上叠加(不存在按 0 起算)。"""
        by = rec.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            return
        entry = self._data.get(key)
        if entry is None:
            self._data[key] = (by, None)
            return
        value, expire_at = entry
        if isinstance(value, bool) or not isinstance(value, int):
            return  # 原值非整数, 重放无法累加; 在线写不会产生此记录
        self._data[key] = (value + by, expire_at)

    # ------------------------------------------------------------------ #
    # 公共 API
    # ------------------------------------------------------------------ #
    def put(self, key: str, value: Any, ttl: Optional[float]) -> None:
        """写入键; 同时把 put 记录追加到 WAL。"""
        with self._lock:
            expire_at = None if ttl is None else self._now() + float(ttl)
            record = {
                "op": "put",
                "key": key,
                "value": value,
                "ttl": ttl,
                "ts": self._wall(),
            }
            self._append_wal(record)  # 可能因不可序列化而抛错
            self._data[key] = (value, expire_at)

    def get(self, key: str) -> Optional[Any]:
        """取值; 不存在/已过期返回 None(用 ``has`` 区分 value=None 的情况)。"""
        with self._lock:
            entry = self._live(key)
            return None if entry is None else entry[0]

    def has(self, key: str) -> bool:
        with self._lock:
            return self._live(key) is not None

    def delete(self, key: str) -> bool:
        """删除键; 返回是否命中(已过期的键视为不存在, 返回 False)。"""
        with self._lock:
            if self._live(key) is None:
                return False
            self._append_wal({"op": "delete", "key": key, "ts": self._wall()})
            self._data.pop(key, None)
            return True

    def incr(self, key: str, by: int = 1) -> int:
        """整数自增; 键不存在按 0 起算。目标存在但非整数时抛 ``NotIntError``。

        保留原键的 TTL(与 Redis 语义一致)。
        """
        with self._lock:
            entry = self._live(key)
            if entry is None:
                base, expire_at = 0, None
            else:
                base, expire_at = entry
                if isinstance(base, bool) or not isinstance(base, int):
                    raise NotIntError(key)
            self._append_wal(
                {"op": "incr", "key": key, "by": by, "ts": self._wall()}
            )
            new_value = base + by
            self._data[key] = (new_value, expire_at)
            return new_value

    def expires_in(self, key: str) -> Optional[float]:
        """剩余 TTL 秒数(浮点); 无 TTL 或键不存在返回 None。"""
        with self._lock:
            entry = self._live(key)
            if entry is None:
                return None
            _, expire_at = entry
            if expire_at is None:
                return None
            return max(0.0, expire_at - self._now())

    def stats(self) -> dict:
        """返回 ``{"count": 未过期键数, "expired": 累计过期清除数}``。

        count 通过一次全表扫描得到, 扫描同时完成各键的惰性清除。
        """
        with self._lock:
            now = self._now()
            dead: List[str] = [
                k
                for k, (_, exp) in self._data.items()
                if exp is not None and now >= exp
            ]
            for k in dead:
                del self._data[k]
            self._expired += len(dead)
            return {"count": len(self._data), "expired": self._expired}

    def uptime_ms(self) -> int:
        return int((self._now() - self._t0) * 1000)
