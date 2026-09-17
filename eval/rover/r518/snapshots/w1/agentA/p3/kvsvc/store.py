"""存储内核：内存字典 + TTL 惰性过期 + WAL 追加日志 + 线程安全。

设计要点
--------
* 进程内状态形态: ``{key: {"value": Any, "expires_at": float | None}}``
  ``expires_at`` 为绝对墙上时钟秒 (``time.time()``)，重启后仍可在同一时间轴比较；
  为 ``None`` 表示永不过期。
* 惰性过期: 每次操作前先清理已过期键，并累计到 ``expired`` 计数。
* WAL: put / delete / incr 成功后在锁内追加一行 JSON，至少含 ``op`` 与 ``key``。
* 重放: 按写入顺序重建状态；重放时已过期的记录不复活，并计入 ``expired``。
"""

import json
import os
import threading
import time


class KVStore:
    """线程安全的带 TTL 键值存储。"""

    def __init__(self, wal_path):
        self._lock = threading.RLock()
        self._data = {}
        self._expired = 0
        self._started = time.monotonic()
        self._wal_path = os.path.abspath(wal_path)
        parent = os.path.dirname(self._wal_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._replay()
        self._wal = open(self._wal_path, "a", encoding="utf-8", newline="\n")

    # ---------------- 内部实现 ----------------

    def _replay(self):
        """按 WAL 顺序重建内存状态（构造期单线程执行，无需持锁）。"""
        now = time.time()
        if not os.path.exists(self._wal_path):
            return
        entries = {}
        with open(self._wal_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # 容忍尾部半行 / 损坏行
                if not isinstance(rec, dict):
                    continue
                op = rec.get("op")
                key = rec.get("key")
                if op not in ("put", "incr", "delete") or not isinstance(key, str):
                    continue
                if op == "delete":
                    entries.pop(key, None)
                else:
                    # put / incr 都把该次写操作后的最终值写入 WAL，
                    # 因此重放对两者都等价于直接赋值。
                    entries[key] = {
                        "value": rec.get("value"),
                        "expires_at": rec.get("expires_at"),
                    }
        for key, ent in entries.items():
            exp = ent["expires_at"]
            if exp is not None and (isinstance(exp, bool) or not isinstance(exp, (int, float))):
                exp = None
                ent["expires_at"] = None
            if exp is not None and exp <= now:
                # 已过期的键不得复活；它确实"因过期被清除"，计入 expired。
                self._expired += 1
                continue
            self._data[key] = ent

    def _purge_locked(self, now):
        """惰性清理已过期键（调用方必须持锁）。"""
        dead = [
            k for k, ent in self._data.items()
            if ent["expires_at"] is not None and ent["expires_at"] <= now
        ]
        for k in dead:
            del self._data[k]
            self._expired += 1

    def _append(self, rec):
        """在锁内追加一行 WAL 并 flush（进程被 kill 后仍可完整重放）。"""
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
        self._wal.write(line)
        self._wal.flush()

    @staticmethod
    def _expires_in(ent, now):
        exp = ent["expires_at"]
        return None if exp is None else exp - now

    # ---------------- 对外操作 ----------------

    def put(self, key, value, ttl):
        """写入键值；ttl 为 None 表示永不过期，否则为秒数（可为小数）。"""
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            expires_at = None if ttl is None else now + float(ttl)
            ent = {"value": value, "expires_at": expires_at}
            self._data[key] = ent
            self._append({
                "op": "put", "key": key, "value": value,
                "expires_at": expires_at, "ts": now,
            })
            return {"key": key, "value": value, "expires_in": self._expires_in(ent, now)}

    def get(self, key):
        """返回 ``{"key","value"}``；键不存在或已过期返回 None。"""
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            ent = self._data.get(key)
            if ent is None:
                return None
            return {"key": key, "value": ent["value"]}

    def delete(self, key):
        """删除键；返回是否真的删除了一个未过期的键。"""
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            if key not in self._data:
                return False
            del self._data[key]
            self._append({"op": "delete", "key": key, "ts": now})
            return True

    def incr(self, key, by):
        """整数自增；返回 ``(status, value)``，status ∈ {"ok", "not_int"}。

        键不存在（或已过期）按 0 起算；原值不是整数返回 "not_int"。
        已存在且未过期的键保留其原到期时间。
        """
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            ent = self._data.get(key)
            if ent is None:
                new_value = int(by)
                expires_at = None
            else:
                cur = ent["value"]
                if isinstance(cur, bool) or not isinstance(cur, int):
                    return ("not_int", None)
                new_value = cur + int(by)
                expires_at = ent["expires_at"]
            self._data[key] = {"value": new_value, "expires_at": expires_at}
            self._append({
                "op": "incr", "key": key, "by": int(by),
                "value": new_value, "expires_at": expires_at, "ts": now,
            })
            return ("ok", new_value)

    def stats(self):
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int((time.monotonic() - self._started) * 1000),
            }

    def close(self):
        with self._lock:
            try:
                self._wal.flush()
                self._wal.close()
            except Exception:
                pass
