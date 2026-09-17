"""线程安全、带 TTL 的键值存储，并支持基于 WAL 的持久化重放。"""

import json
import threading
import time
from typing import Any, Dict, Optional, Tuple


class NotIntError(Exception):
    """对非整数值执行 incr 时抛出。"""


class KeyState:
    __slots__ = ("value", "expire_at")

    def __init__(self, value: Any, expire_at: Optional[float]) -> None:
        self.value = value
        self.expire_at = expire_at


class KVStore:
    """内存键值表 + 追加写 WAL。

    所有公开方法都是线程安全的；WAL 写入在锁内完成，保证日志顺序与
    状态变更顺序一致，重启重放后能恢复到相同状态。
    """

    def __init__(self, wal_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, KeyState] = {}
        self._expired = 0
        self._start = time.monotonic()
        self._wal_path = wal_path
        self._wal = None
        if wal_path:
            self._wal = open(wal_path, "a", encoding="utf-8")

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _now() -> float:
        """单调时钟，仅用于 uptime_ms 计算。"""
        return time.monotonic()

    @staticmethod
    def _wall() -> float:
        """挂钟时间，用于 TTL 判断，跨进程重启仍然可比。"""
        return time.time()

    def _expired_locked(self, st: "KeyState") -> bool:
        return st.expire_at is not None and st.expire_at <= self._wall()

    def _purge_locked(self, key: str) -> None:
        """惰性清除：若 key 已过期，删除并计入 expired。"""
        st = self._data.get(key)
        if st is not None and self._expired_locked(st):
            del self._data[key]
            self._expired += 1

    def _purge_all_locked(self) -> None:
        for key in [k for k, s in self._data.items() if self._expired_locked(s)]:
            del self._data[key]
            self._expired += 1

    def _wal_append_locked(self, record: Dict[str, Any]) -> None:
        if self._wal is None:
            return
        self._wal.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._wal.flush()

    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    @staticmethod
    def _is_num(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    # ------------------------------------------------------------------- api
    def put(self, key: str, value: Any, ttl: Optional[float]) -> float:
        """写入键值，返回剩余秒数（未设 ttl 时返回 0）。"""
        with self._lock:
            now = self._wall()
            expire_at = now + ttl if ttl is not None else None
            self._data[key] = KeyState(value, expire_at)
            record: Dict[str, Any] = {"op": "put", "key": key, "value": value,
                                      "ts": now}
            if ttl is not None:
                record["ttl"] = ttl
            self._wal_append_locked(record)
            return ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            self._purge_locked(key)
            st = self._data.get(key)
            return st.value if st is not None else None

    def exists(self, key: str) -> bool:
        with self._lock:
            self._purge_locked(key)
            return key in self._data

    def delete(self, key: str) -> bool:
        with self._lock:
            self._purge_locked(key)
            if key not in self._data:
                return False
            del self._data[key]
            self._wal_append_locked({"op": "delete", "key": key})
            return True

    def incr(self, key: str, by: int = 1) -> int:
        with self._lock:
            self._purge_locked(key)
            st = self._data.get(key)
            if st is None:
                base = 0
                expire_at = None
            else:
                if not self._is_int(st.value):
                    raise NotIntError(key)
                base = st.value
                expire_at = st.expire_at
            new_value = base + by
            self._data[key] = KeyState(new_value, expire_at)
            record = {"op": "incr", "key": key, "by": by,
                      "value": new_value, "ts": self._wall()}
            if expire_at is not None:
                record["expire_at"] = expire_at
            self._wal_append_locked(record)
            return new_value

    def stats(self) -> Tuple[int, int, int]:
        with self._lock:
            self._purge_all_locked()
            uptime_ms = int((self._now() - self._start) * 1000)
            return len(self._data), self._expired, uptime_ms

    def remaining(self, key: str) -> Optional[float]:
        """返回键的剩余 TTL 秒数；不存在或无 TTL 时返回 None。"""
        with self._lock:
            st = self._data.get(key)
            if st is None or st.expire_at is None or self._expired_locked(st):
                return None
            return max(0.0, st.expire_at - self._wall())

    # --------------------------------------------------------------- replay
    def load_wal(self) -> None:
        """从 WAL 重放历史记录，恢复未过期的键值。"""
        if not self._wal_path:
            return
        try:
            with open(self._wal_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            return
        with self._lock:
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if not isinstance(record, dict):
                    continue
                self._apply_record_locked(record)
            self._purge_all_locked()

    def _apply_record_locked(self, record: Dict[str, Any]) -> None:
        op = record.get("op")
        key = record.get("key")
        if not isinstance(key, str):
            return
        st = self._data.get(key)
        if st is not None and self._expired_locked(st):
            # 记录生效前该键已过期：视为不存在。
            del self._data[key]
            st = None
        if op == "put":
            expire_at = None
            if self._is_num(record.get("ttl")):
                base = record.get("ts")
                if not self._is_num(base):
                    base = self._wall()
                expire_at = float(base) + float(record["ttl"])
            self._data[key] = KeyState(record.get("value"), expire_at)
        elif op == "delete":
            self._data.pop(key, None)
        elif op == "incr":
            by = record.get("by", 1)
            if not self._is_int(by) or (st is not None and not self._is_int(st.value)):
                return
            new_value = (0 if st is None else st.value) + by
            expire_at = None if st is None else st.expire_at
            if self._is_num(record.get("expire_at")):
                expire_at = float(record["expire_at"])
            elif self._is_num(record.get("ttl")):
                base_ts = record.get("ts")
                if not self._is_num(base_ts):
                    base_ts = self._wall()
                expire_at = float(base_ts) + float(record["ttl"])
            if self._is_int(record.get("value")):
                new_value = record["value"]
            self._data[key] = KeyState(new_value, expire_at)

    def close(self) -> None:
        with self._lock:
            if self._wal is not None:
                try:
                    self._wal.flush()
                    self._wal.close()
                finally:
                    self._wal = None
