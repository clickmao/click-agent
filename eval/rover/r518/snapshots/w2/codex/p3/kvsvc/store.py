"""Thread-safe key-value store with TTL and write-ahead-log persistence."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, Optional


class KVStore:
    """In-memory KV store guarded by a reentrant lock.

    Every mutation is appended to the WAL as a single JSON line, so state can
    be rebuilt after a restart.
    """

    def __init__(self, wal_path: str) -> None:
        self._wal_path = wal_path
        self._lock = threading.RLock()
        # key -> [value, expire_at or None]
        self._data: Dict[str, list] = {}
        self._expired = 0
        self._wal = None
        self._replay_wal()

    # -- lifecycle ---------------------------------------------------------
    def _replay_wal(self) -> None:
        try:
            with open(self._wal_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(rec, dict):
                        continue
                    self._apply_record(rec, persist=False, now=time.time())
        except FileNotFoundError:
            pass

    def _apply_record(self, rec: dict, persist: bool, now: float) -> None:
        op = rec.get("op")
        key = rec.get("key")
        if not isinstance(key, str):
            return
        if op == "put":
            ttl = rec.get("ttl")
            expire_at = None
            if isinstance(ttl, (int, float)) and not isinstance(ttl, bool):
                expire_at = now + float(ttl)
            self._data[key] = [rec.get("value"), expire_at]
        elif op == "delete":
            self._data.pop(key, None)
        elif op == "incr":
            cur = self._data.get(key)
            if cur is None:
                base = 0
            else:
                base = cur[0] if isinstance(cur[0], int) and not isinstance(cur[0], bool) else 0
            by = rec.get("by", 1)
            if not isinstance(by, int) or isinstance(by, bool):
                by = 1
            value = base + by
            expire_at = cur[1] if cur is not None else None
            self._data[key] = [value, expire_at]
        if persist:
            self._append_wal(rec)

    def _append_wal(self, rec: dict) -> None:
        if self._wal is None:
            self._wal = open(self._wal_path, "a", encoding="utf-8")
        self._wal.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._wal.flush()

    def close(self) -> None:
        with self._lock:
            if self._wal is not None:
                try:
                    self._wal.close()
                finally:
                    self._wal = None

    # -- internals ---------------------------------------------------------
    @staticmethod
    def _alive(entry: Optional[list], now: float) -> bool:
        if entry is None:
            return False
        expire_at = entry[1]
        return expire_at is None or expire_at > now

    def _purge(self, key: str, now: float) -> bool:
        """Drop the key if expired. Returns True if the key is present & alive."""
        entry = self._data.get(key)
        if entry is None:
            return False
        if self._alive(entry, now):
            return True
        del self._data[key]
        self._expired += 1
        return False

    def _sweep(self, now: float) -> None:
        dead = [k for k, v in self._data.items() if not self._alive(v, now)]
        for k in dead:
            del self._data[k]
            self._expired += 1

    # -- public API --------------------------------------------------------
    def put(self, key: str, value: Any, ttl: Optional[float]) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            entry = self._data.get(key)
            if entry is not None:
                self._purge(key, now)
            expire_at = None
            if ttl is not None:
                expire_at = now + float(ttl)
            self._data[key] = [value, expire_at]
            self._apply_record(
                {"op": "put", "key": key, "value": value, "ttl": ttl},
                persist=True,
                now=now,
            )
            return self.describe(key, now)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if not self._purge(key, time.time()):
                return None
            return self._data[key][0]

    def describe(self, key: str, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Return the response payload for a PUT without re-taking the lock."""
        if now is None:
            now = time.time()
        entry = self._data.get(key)
        if not self._alive(entry, now):
            return None
        expire_at = entry[1]
        expires_in = None if expire_at is None else max(0.0, expire_at - now)
        return {"key": key, "value": entry[0], "expires_in": expires_in}

    def delete(self, key: str) -> bool:
        with self._lock:
            if not self._purge(key, time.time()):
                return False
            del self._data[key]
            self._apply_record({"op": "delete", "key": key}, persist=True, now=time.time())
            return True

    def incr(self, key: str, by: int) -> Dict[str, Any]:
        """Returns {"ok": True, "value": n} or {"ok": False} for non-int values."""
        with self._lock:
            now = time.time()
            if self._purge(key, now):
                cur = self._data[key][0]
                if not isinstance(cur, int) or isinstance(cur, bool):
                    return {"ok": False}
                value = cur + by
                self._data[key][0] = value
            else:
                value = by
                self._data[key] = [value, None]
            self._apply_record({"op": "incr", "key": key, "by": by}, persist=True, now=now)
            return {"ok": True, "value": value}

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._sweep(time.time())
            return {"count": len(self._data), "expired": self._expired}
