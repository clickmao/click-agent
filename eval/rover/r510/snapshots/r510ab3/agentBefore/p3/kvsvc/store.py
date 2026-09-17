"""带 TTL 的键值存储核心，WAL 持久化，线程安全。

对外不变式:
  * put/get/delete/incr 均在单把可重入锁内完成，保证 incr 不丢更新。
  * 未设 ttl 的键其 expires_at 为 None。
  * 过期时刻用 **epoch 秒** (time.time()) 记录，跨进程一致；
    WAL 中直接落绝对 expires_at，重启后已过期的键不得复活。
  * 惰性过期: 读到/写到过期键时清除并累计 expired 计数。
  * 每次写操作追加一行 JSON 到 WAL (op ∈ {put, delete, incr})。
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple


class WALError(RuntimeError):
    """WAL 打开/写入失败。"""


class KVStore:
    """线程安全的 TTL 键值存储。"""

    def __init__(self, wal_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        # key -> (value, expires_at_epoch_seconds_or_None)
        self._data: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._expired_count = 0
        self._start_monotonic = time.monotonic()
        self._wal_path = wal_path
        self._wal_fh = None
        if wal_path:
            self._open_wal(wal_path)
            self._replay_wal(wal_path)

    # ---------------- 进程信息 ----------------

    def uptime_ms(self) -> int:
        return int((time.monotonic() - self._start_monotonic) * 1000)

    # ---------------- WAL ----------------

    def _open_wal(self, wal_path: str) -> None:
        parent = os.path.dirname(os.path.abspath(wal_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        try:
            self._wal_fh = open(wal_path, "a", encoding="utf-8", newline="\n")
        except OSError as exc:  # pragma: no cover - 环境相关
            raise WALError(f"cannot open WAL {wal_path!r}: {exc}") from exc

    def _append_wal(self, record: dict) -> None:
        if self._wal_fh is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal_fh.write(line + "\n")
        self._wal_fh.flush()
        try:
            os.fsync(self._wal_fh.fileno())
        except OSError:  # pragma: no cover - 某些文件系统不支持
            pass

    def _replay_wal(self, wal_path: str) -> None:
        if not os.path.exists(wal_path):
            return
        now = time.time()
        with open(wal_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    # 半截行(崩溃写入)，跳过，不阻断恢复
                    continue
                if not isinstance(rec, dict):
                    continue
                op = rec.get("op")
                key = rec.get("key")
                if not isinstance(key, str):
                    continue
                exp = rec.get("expires_at")
                if isinstance(exp, bool) or not isinstance(exp, (int, float)):
                    exp = None
                else:
                    exp = float(exp)
                if op == "put":
                    if exp is not None and exp <= now:
                        # 已过期: 不得复活
                        self._expired_count += 1
                        self._data.pop(key, None)
                        continue
                    self._data[key] = (rec.get("value"), exp)
                elif op == "delete":
                    self._data.pop(key, None)
                elif op == "incr":
                    cur_val, cur_exp = self._data.get(key, (0, None))
                    if cur_exp is not None and cur_exp <= now:
                        self._expired_count += 1
                        cur_val, cur_exp = 0, None
                    by = rec.get("by", 1)
                    if not isinstance(by, int) or isinstance(by, bool):
                        by = 1
                    if isinstance(cur_val, bool) or not isinstance(cur_val, int):
                        cur_val = 0
                    self._data[key] = (cur_val + by, cur_exp)
                # 未知 op 忽略

    def close(self) -> None:
        with self._lock:
            if self._wal_fh is not None:
                try:
                    self._wal_fh.close()
                finally:
                    self._wal_fh = None

    # ---------------- 内部工具 ----------------

    def _purge_if_expired(self, key: str, now: float) -> bool:
        """若 key 已过期则清除；返回是否存在且有效。调用者须持锁。"""
        entry = self._data.get(key)
        if entry is None:
            return False
        _, expires_at = entry
        if expires_at is not None and expires_at <= now:
            del self._data[key]
            self._expired_count += 1
            return False
        return True

    def _sweep(self, now: float) -> None:
        """全量惰性清扫，使 count/expired 统计准确。调用者须持锁。"""
        dead = [
            k
            for k, (_, exp) in self._data.items()
            if exp is not None and exp <= now
        ]
        for k in dead:
            del self._data[k]
            self._expired_count += 1

    @staticmethod
    def _normalize_ttl(ttl: Any) -> Optional[float]:
        if ttl is None:
            return None
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise TypeError("ttl must be a number")
        ttl = float(ttl)
        if math.isnan(ttl) or math.isinf(ttl):
            raise TypeError("ttl must be finite")
        return ttl

    # ---------------- 公共 API ----------------

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> Optional[float]:
        """写入键值，返回剩余秒数(无 ttl 则 None)。"""
        ttl_f = self._normalize_ttl(ttl)
        now = time.time()
        with self._lock:
            if ttl_f is None:
                expires_at = None
                expires_in = None
            else:
                expires_at = now + ttl_f
                expires_in = ttl_f
            self._data[key] = (value, expires_at)
            # WAL 落绝对 expires_at，跨进程重放语义一致
            self._append_wal(
                {"op": "put", "key": key, "value": value, "expires_at": expires_at}
            )
            return expires_in

    def get(self, key: str) -> Optional[Tuple[Any, Optional[float]]]:
        """返回 (value, expires_in) 或 None(不存在/已过期)。"""
        now = time.time()
        with self._lock:
            if not self._purge_if_expired(key, now):
                return None
            value, expires_at = self._data[key]
            if expires_at is None:
                return value, None
            return value, max(0.0, expires_at - now)

    def delete(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            if not self._purge_if_expired(key, now):
                return False
            del self._data[key]
            self._append_wal({"op": "delete", "key": key})
            return True

    def incr(self, key: str, by: int = 1) -> Tuple[bool, Any]:
        """原子自增。

        返回 (ok, value_or_reason):
          (True, new_int)   成功
          (False, "not_int") 原值存在且不是整数
        """
        if isinstance(by, bool) or not isinstance(by, int):
            raise TypeError("by must be an int")
        now = time.time()
        with self._lock:
            if self._purge_if_expired(key, now):
                cur_val, cur_exp = self._data[key]
                if isinstance(cur_val, bool) or not isinstance(cur_val, int):
                    return False, "not_int"
                base = cur_val
                expires_at = cur_exp
            else:
                base = 0
                expires_at = None
            new_val = base + by
            # 保留原 TTL（未过期的键），新键无 TTL
            self._data[key] = (new_val, expires_at)
            self._append_wal({"op": "incr", "key": key, "by": by})
            return True, new_val

    def stats(self) -> Dict[str, int]:
        now = time.time()
        with self._lock:
            self._sweep(now)
            return {
                "count": len(self._data),
                "expired": self._expired_count,
                "uptime_ms": self.uptime_ms(),
            }
