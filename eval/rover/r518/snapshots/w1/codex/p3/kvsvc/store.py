"""In-memory key/value store with TTL expiry and a JSON-lines WAL.

Only the Python standard library is used.  The store is thread safe: all
mutations and reads go through a single re-entrant lock, which also guarantees
that the WAL append and the in-memory mutation happen atomically with respect
to each other (no lost updates).
"""

import json
import os
import threading
import time

_NOT_FOUND = object()


class Store:
    def __init__(self, wal_path=None, logger=None):
        self._lock = threading.RLock()
        self._data = {}          # key -> {"value": any, "expire_at": float|None}
        self._expired = 0        # cumulative count of keys removed because of TTL
        self._wal_path = wal_path
        self._wal = None
        self._started_at = time.monotonic()
        self._logger = logger
        if wal_path:
            directory = os.path.dirname(os.path.abspath(wal_path))
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._replay(wal_path)
            self._wal = open(wal_path, "a", encoding="utf-8")

    # ------------------------------------------------------------------ WAL
    def _wal_append(self, record):
        if self._wal is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal.write(line + "\n")
        self._wal.flush()
        os.fsync(self._wal.fileno())

    def _log(self, message):
        if self._logger is not None:
            self._logger(message)

    def _replay(self, path):
        """Rebuild state from the WAL, honouring expiry timestamps."""
        if not os.path.exists(path):
            return
        now_wall = time.time()
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    self._log("skipping malformed WAL line: %r" % (line,))
                    continue
                if not isinstance(record, dict):
                    continue
                self._apply_record(record, now_wall)

    def _apply_record(self, record, now_wall):
        op = record.get("op")
        key = record.get("key")
        if not isinstance(key, str):
            return
        if op == "delete":
            self._data.pop(key, None)
            return
        if op not in ("put", "incr"):
            return
        expire_at = record.get("expire_at")
        if expire_at is not None:
            try:
                expire_at = float(expire_at)
            except (TypeError, ValueError):
                expire_at = None
        if expire_at is not None and expire_at <= now_wall:
            # Expired before restart: it must not come back to life.
            self._data.pop(key, None)
            return
        if op == "incr":
            current = self._data.get(key)
            base = 0
            if current is not None:
                value = current["value"]
                if isinstance(value, int) and not isinstance(value, bool):
                    base = value
                else:
                    base = 0
            value = base + int(record.get("by", 1))
        else:
            value = record.get("value")
        self._data[key] = {"value": value, "expire_at": expire_at}

    # --------------------------------------------------------------- helpers
    def _purge_expired_locked(self, now):
        """Drop every key whose TTL elapsed; returns nothing, bumps counter."""
        dead = [k for k, item in self._data.items()
                if item["expire_at"] is not None and item["expire_at"] <= now]
        for key in dead:
            self._data.pop(key, None)
            self._expired += 1

    def _lookup_locked(self, key, now):
        item = self._data.get(key)
        if item is None:
            return None
        if item["expire_at"] is not None and item["expire_at"] <= now:
            self._data.pop(key, None)
            self._expired += 1
            return None
        return item

    def _remaining(self, item, now):
        if item["expire_at"] is None:
            return None
        remaining = item["expire_at"] - now
        if remaining < 0:
            remaining = 0.0
        return remaining

    # ------------------------------------------------------------ public API
    def put(self, key, value, ttl=None):
        now = time.time()
        expire_at = None
        if ttl is not None:
            expire_at = now + float(ttl)
        with self._lock:
            self._purge_expired_locked(now)
            self._data[key] = {"value": value, "expire_at": expire_at}
            item = self._data[key]
            self._wal_append({
                "op": "put",
                "key": key,
                "value": value,
                "ttl": ttl,
                "expire_at": expire_at,
                "ts": now,
            })
            return {
                "key": key,
                "value": value,
                "expires_in": self._remaining(item, now),
            }

    def get(self, key):
        now = time.time()
        with self._lock:
            item = self._lookup_locked(key, now)
            if item is None:
                return None
            return {"key": key, "value": item["value"]}

    def delete(self, key):
        now = time.time()
        with self._lock:
            item = self._lookup_locked(key, now)
            if item is None:
                return False
            self._data.pop(key, None)
            self._wal_append({"op": "delete", "key": key, "ts": now})
            return True

    def incr(self, key, by=1):
        now = time.time()
        with self._lock:
            item = self._lookup_locked(key, now)
            base = 0
            if item is not None:
                value = item["value"]
                if not isinstance(value, int) or isinstance(value, bool):
                    return None  # not an int -> 409
                base = value
            value = base + int(by)
            expire_at = item["expire_at"] if item is not None else None
            self._data[key] = {"value": value, "expire_at": expire_at}
            self._wal_append({
                "op": "incr",
                "key": key,
                "by": int(by),
                "value": value,
                "expire_at": expire_at,
                "ts": now,
            })
            return {"key": key, "value": value}

    def stats(self):
        now = time.time()
        with self._lock:
            self._purge_expired_locked(now)
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int((time.monotonic() - self._started_at) * 1000),
            }

    def close(self):
        with self._lock:
            if self._wal is not None:
                try:
                    self._wal.flush()
                    os.fsync(self._wal.fileno())
                finally:
                    self._wal.close()
                    self._wal = None
