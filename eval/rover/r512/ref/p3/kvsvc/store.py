# -*- coding: utf-8 -*-
"""R508 P3 参考解 (oracle): kvsvc 包 —— store 层 (线程安全 + TTL + WAL)。"""
from __future__ import annotations
import json
import threading
import time


class Store:
    def __init__(self, wal_path: str):
        self._lock = threading.RLock()
        self._d: dict = {}
        self._expired = 0
        self._wal = wal_path
        self._t0 = time.time()
        self._replay()

    # --- WAL ---
    def _replay(self) -> None:
        try:
            with open(self._wal, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            return
        now = time.time()
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            op = rec.get("op")
            k = rec.get("key")
            if not isinstance(k, str):
                continue
            exp = rec.get("expires_at")
            if op in ("put", "incr"):
                if exp is not None and exp <= now:
                    continue
                self._d[k] = [rec.get("value"), exp]
            elif op == "delete":
                self._d.pop(k, None)

    def _append(self, rec: dict) -> None:
        try:
            with open(self._wal, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _purge(self, key: str, now: float):
        v = self._d.get(key)
        if v is not None and v[1] is not None and v[1] <= now:
            self._d.pop(key, None)
            self._expired += 1
            return None
        return v

    def _purge_all(self, now: float) -> None:
        for k in list(self._d.keys()):
            self._purge(k, now)

    # --- API ---
    def put(self, key: str, value, ttl) -> dict:
        with self._lock:
            now = time.time()
            exp = (now + float(ttl)) if ttl is not None else None
            self._d[key] = [value, exp]
            self._append({"op": "put", "key": key, "value": value, "expires_at": exp, "ts": now})
            return {"key": key, "value": value, "expires_in": (float(ttl) if ttl is not None else None)}

    def get(self, key: str):
        with self._lock:
            v = self._purge(key, time.time())
            return None if v is None else {"key": key, "value": v[0]}

    def delete(self, key: str) -> bool:
        with self._lock:
            now = time.time()
            if self._purge(key, now) is None:
                return False
            self._d.pop(key, None)
            self._append({"op": "delete", "key": key, "ts": now})
            return True

    def incr(self, key: str, by: int):
        with self._lock:
            now = time.time()
            v = self._purge(key, now)
            cur = 0 if v is None else v[0]
            if isinstance(cur, bool) or not isinstance(cur, int):
                return "not_int"
            nv = cur + by
            exp = v[1] if v is not None else None
            self._d[key] = [nv, exp]
            self._append({"op": "incr", "key": key, "by": by, "value": nv, "expires_at": exp, "ts": now})
            return {"key": key, "value": nv}

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            self._purge_all(now)
            return {"count": len(self._d), "expired": self._expired,
                    "uptime_ms": int((now - self._t0) * 1000)}
