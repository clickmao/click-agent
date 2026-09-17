"""kvsvc.store —— 线程安全、带 TTL、带 WAL 持久化的键值存储核心。

语义要点合约:
  * count   = 当前未过期键数
  * expired = 累计因过期被清除的键数 (惰性清除时结算)
  * 所有写操作(put/delete/incr)先原子写 WAL 再改内存; 重放时逐行 apply 不重复写 WAL。
  * 重放规则: 过期时刻用「WAL 内记录的绝对时刻(毫秒时间戳)」判定,
              重放时刻已过期的键不得复活。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple


class KVStore:
    """带过期时间与 WAL 的键值存储。所有公开方法均线程安全。"""

    def __init__(self, wal_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        # key -> (value, expire_at_monotonic or None, wall_expire_ms or None)
        self._data: Dict[str, Tuple[Any, Optional[float], Optional[int]]] = {}
        self._expired = 0          # 累计过期清除计数
        self._start_mono = time.monotonic()
        self._wal_path = wal_path
        self._wal_fp = None
        if wal_path:
            parent = os.path.dirname(os.path.abspath(wal_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._wal_fp = open(wal_path, "a", encoding="utf-8", newline="\n")

    # ---------------------------------------------------------------- WAL --

    def _wal_append(self, record: dict) -> None:
        """必须在持有锁时调用: 追加一行 JSON 并 flush 落盘。"""
        if self._wal_fp is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal_fp.write(line + "\n")
        self._wal_fp.flush()
        os.fsync(self._wal_fp.fileno())

    # ------------------------------------------------------------- 重放 --

    def replay(self) -> None:
        """从 WAL 重放恢复状态。已过期的键不会复活, 也不计入 expired。"""
        if not self._wal_path or not os.path.exists(self._wal_path):
            return
        now_wall_ms = int(time.time() * 1000)
        now_mono = time.monotonic()
        with self._lock:
            with open(self._wal_path, "r", encoding="utf-8") as fp:
                for raw in fp:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        # 半截行(WAL 尾部损坏) -> 跳过, 不阻断恢复
                        continue
                    self._apply_replay(rec, now_wall_ms, now_mono)

    def _apply_replay(self, rec: dict, now_wall_ms: int, now_mono: float) -> None:
        op = rec.get("op")
        key = rec.get("key")
        if not isinstance(key, str):
            return
        # 先惰性结算该键, 避免过期键复活
        self._purge_one(key, now_wall_ms)

        if op == "put":
            exp_ms = rec.get("expire_at_ms")
            if exp_ms is not None and exp_ms <= now_wall_ms:
                # 该记录落盘时已过期 -> 不复活
                self._data.pop(key, None)
                return
            if exp_ms is None:
                self._data[key] = (rec.get("value"), None, None)
            else:
                remain = (exp_ms - now_wall_ms) / 1000.0
                self._data[key] = (rec.get("value"), now_mono + remain, exp_ms)
        elif op == "delete":
            self._data.pop(key, None)
        elif op == "incr":
            cur, exp_mono, exp_ms = self._data.get(key, (None, None, None))
            if not isinstance(cur, int) or isinstance(cur, bool):
                cur_int = 0
                # 原值非整数时 incr 应报 not_int; 重放期以 0 起算保持确定
                if cur is None:
                    cur_int = 0
            else:
                cur_int = cur
            if not isinstance(cur, int) or isinstance(cur, bool):
                cur_int = rec.get("value", 0)
                self._data[key] = (cur_int, None, None)
            else:
                self._data[key] = (cur_int + int(rec.get("by", 1)), exp_mono, exp_ms)

    # ------------------------------------------------------------ 惰性清除 --

    def _purge_one(self, key: str, now_wall_ms: Optional[int] = None) -> bool:
        """结算单个键的过期。返回是否发生了过期清除。调用方需持锁。"""
        item = self._data.get(key)
        if item is None:
            return False
        _, exp_mono, exp_ms = item
        if exp_mono is None:
            return False
        if time.monotonic() >= exp_mono:
            del self._data[key]
            self._expired += 1
            return True
        return False

    def _purge_all(self) -> None:
        """全局惰性清除, 结算 expired 计数。调用方需持锁。"""
        now = time.monotonic()
        dead = [k for k, (_, em, _) in self._data.items() if em is not None and now >= em]
        for k in dead:
            del self._data[k]
        self._expired += len(dead)

    # -------------------------------------------------------------- 读写 --

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> dict:
        with self._lock:
            self._purge_one(key)
            now_mono = time.monotonic()
            now_wall_ms = int(time.time() * 1000)
            exp_mono = now_mono + ttl if ttl is not None else None
            exp_ms = now_wall_ms + int(round(ttl * 1000)) if ttl is not None else None
            self._wal_append({
                "op": "put", "key": key, "value": value,
                "ttl": ttl, "expire_at_ms": exp_ms,
            })
            self._data[key] = (value, exp_mono, exp_ms)
            return {"key": key, "value": value, "expires_in": ttl}

    def get(self, key: str) -> Optional[Any]:
        """返回 (True, value) 或 (False, None)。"""
        with self._lock:
            if self._purge_one(key):
                return None
            item = self._data.get(key)
            if item is None:
                return None
            return item[0]

    def exists(self, key: str) -> bool:
        with self._lock:
            self._purge_one(key)
            return key in self._data

    def get_expires_in(self, key: str) -> Any:
        with self._lock:
            if self._purge_one(key):
                return None
            item = self._data.get(key)
            if item is None:
                return None
            _, exp_mono, _ = item
            if exp_mono is None:
                return None
            return max(0.0, exp_mono - time.monotonic())

    def delete(self, key: str) -> bool:
        with self._lock:
            if self._purge_one(key):
                return False
            if key not in self._data:
                return False
            self._wal_append({"op": "delete", "key": key})
            del self._data[key]
            return True

    def incr(self, key: str, by: int = 1) -> Tuple[bool, Any]:
        """返回 (ok, value_or_None)。ok=False 表示原值非整数。"""
        with self._lock:
            self._purge_one(key)
            item = self._data.get(key)
            if item is None:
                cur = 0
                exp_mono = None
                exp_ms = None
            else:
                cur, exp_mono, exp_ms = item
                if not isinstance(cur, int) or isinstance(cur, bool):
                    return False, None
            new_val = cur + by
            self._wal_append({"op": "incr", "key": key, "by": by, "value": new_val})
            self._data[key] = (new_val, exp_mono, exp_ms)
            return True, new_val

    def stats(self) -> dict:
        with self._lock:
            self._purge_all()
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int((time.monotonic() - self._start_mono) * 1000),
            }

    def close(self) -> None:
        with self._lock:
            if self._wal_fp is not None:
                try:
                    self._wal_fp.flush()
                    self._wal_fp.close()
                finally:
                    self._wal_fp = None
