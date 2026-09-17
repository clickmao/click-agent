"""Thread-safe, WAL-backed key-value store with per-key TTL support."""

import json
import os
import threading
import time

__all__ = ["KVStore", "NotIntError"]


class NotIntError(Exception):
    """Raised when an incr operation targets a non-integer value."""


class _Entry:
    __slots__ = ("value", "expire_at")

    def __init__(self, value, expire_at):
        self.value = value
        self.expire_at = expire_at  # absolute monotonic deadline or None


class KVStore:
    """In-memory key-value store with TTL and a write-ahead log.

    A single lock guards both the data map and the WAL file so that every
    mutation is atomic with respect to concurrent readers/writers.
    """

    def __init__(self, wal_path=None):
        self._lock = threading.RLock()
        self._data = {}
        self._expired = 0
        self._start = time.monotonic()
        self._wal_path = wal_path
        self._wal = None
        if wal_path:
            directory = os.path.dirname(os.path.abspath(wal_path))
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._replay(wal_path)
            self._wal = open(wal_path, "a", encoding="utf-8")

    # ------------------------------------------------------------------ WAL
    def _replay(self, wal_path):
        if not os.path.exists(wal_path):
            return
        now = time.time()
        with open(wal_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                self._apply(record, now, from_wal=True)

    def _apply(self, record, now, from_wal=False):
        op = record.get("op")
        key = record.get("key")
        if not isinstance(key, str):
            return
        if op == "put":
            expire_at = record.get("expire_at")
            if expire_at is not None and expire_at <= now:
                # Already expired: never resurrect it.
                self._data.pop(key, None)
                return
            self._data[key] = _Entry(record.get("value"), expire_at)
        elif op == "delete":
            self._data.pop(key, None)
        elif op == "incr":
            entry = self._data.get(key)
            if entry is not None and entry.expire_at is not None and entry.expire_at <= now:
                entry = None
            base = entry.value if entry is not None and _is_int(entry.value) else 0
            by = record.get("by", 1)
            if not _is_int(by):
                by = int(by)
            value = base + by
            expire_at = entry.expire_at if entry is not None else None
            self._data[key] = _Entry(value, expire_at)

    def _append(self, record):
        if self._wal is None:
            return
        self._wal.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._wal.flush()
        os.fsync(self._wal.fileno())

    # -------------------------------------------------------------- helpers
    def _sweep(self, now):
        """Lazily drop expired entries, counting them toward *expired*."""
        dead = [k for k, e in self._data.items() if e.expire_at is not None and e.expire_at <= now]
        for key in dead:
            del self._data[key]
            self._expired += 1

    def _lookup(self, key, now):
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.expire_at is not None and entry.expire_at <= now:
            del self._data[key]
            self._expired += 1
            return None
        return entry

    # ----------------------------------------------------------------- ops
    def put(self, key, value, ttl=None):
        with self._lock:
            now = time.time()
            self._sweep(now)
            expire_at = None
            if ttl is not None:
                expire_at = now + float(ttl)
            self._data[key] = _Entry(value, expire_at)
            self._append({"op": "put", "key": key, "value": value, "expire_at": expire_at})

    def get(self, key):
        with self._lock:
            entry = self._lookup(key, time.time())
            if entry is None:
                return False, None
            return True, entry.value

    def delete(self, key):
        with self._lock:
            now = time.time()
            if self._lookup(key, now) is None:
                return False
            del self._data[key]
            self._append({"op": "delete", "key": key})
            return True

    def incr(self, key, by=1):
        with self._lock:
            now = time.time()
            self._sweep(now)
            entry = self._lookup(key, now)
            base = 0
            if entry is not None:
                if not _is_int(entry.value):
                    raise NotIntError(key)
                base = entry.value
            value = base + by
            expire_at = entry.expire_at if entry is not None else None
            self._data[key] = _Entry(value, expire_at)
            self._append({"op": "incr", "key": key, "by": by})
            return value

    def stats(self):
        with self._lock:
            self._sweep(time.time())
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int((time.monotonic() - self._start) * 1000),
            }

    def close(self):
        with self._lock:
            if self._wal is not None:
                try:
                    self._wal.close()
                finally:
                    self._wal = None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)
