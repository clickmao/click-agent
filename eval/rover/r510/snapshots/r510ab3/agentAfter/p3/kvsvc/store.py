"""带 TTL 的键值存储核心 + 追加式 WAL 持久化（仅标准库）。

并发契约: 所有状态变更都在同一把 threading.Lock 内完成，
因此 8 个并发客户端各做 20 次 incr 的累计值精确等于总增量（无丢更新）。

过期语义: 惰性清除。任何一次访问（get/delete/incr/size）都会先清除已过期键，
被清除的键计入 expired 累计数。重启重放时同样按惰性清除处理，
已过期的键不会复活。
"""

from __future__ import annotations

import io
import json
import os
import threading
import time


class StoredValue:
    """一个键的状态：值（已结构化的 JSON 值）与绝对过期时刻。"""

    __slots__ = ("value", "expire_at")

    def __init__(self, value, expire_at):
        self.value = value
        self.expire_at = expire_at  # 绝对时间戳（time.time() 基准），None = 永不过期


class KVStore:
    """线程安全的 TTL 键值存储，写操作同步追加 WAL。"""

    def __init__(self, wal_path=None):
        self._lock = threading.Lock()
        self._data = {}
        self._expired = 0  # 累计因过期被清除的键数
        self._start = time.monotonic()
        self._wal_path = wal_path
        self._wal = None
        if wal_path:
            parent = os.path.dirname(os.path.abspath(wal_path))
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            # 打开一次并长期持有，保证多线程追加不会交错。
            self._wal = io.open(wal_path, "a", encoding="utf-8", newline="\n")
            self._replay()

    # ---------------- 内部：WAL ----------------

    def _append(self, record):
        if self._wal is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal.write(line + "\n")
        self._wal.flush()

    def _replay(self):
        """从 WAL 重放恢复：只让未过期的键存活。"""
        try:
            with io.open(self._wal_path, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except ValueError:
                        # 半截行（进程被杀）——跳过，不复活脏状态。
                        continue
                    self._apply_record(rec, wall_clock=time.time())
        except FileNotFoundError:
            return

    def _apply_record(self, rec, wall_clock):
        """把一条 WAL 记录应用到内存（重放与实时写入共用）。"""
        op = rec.get("op")
        if op == "put":
            exp = rec.get("expire_at")
            if exp is not None and exp <= wall_clock:
                # 写入时还在，重放时已过期 —— 直接丢弃。
                self._data.pop(rec["key"], None)
                return
            self._data[rec["key"]] = StoredValue(rec.get("value"), exp)
        elif op == "delete":
            self._data.pop(rec["key"], None)
        elif op == "incr":
            # incr 记录里存的是结算后的绝对值，重放幂等。
            if "expire_at" in rec or "value" in rec:
                exp = rec.get("expire_at")
                if exp is not None and exp <= wall_clock:
                    self._data.pop(rec["key"], None)
                    return
                self._data[rec["key"]] = StoredValue(rec.get("value"), exp)

    # ---------------- 内部：过期清除 ----------------

    def _purge_key(self, key, wall_clock):
        """若 key 已过期则清除并计数，返回 True 表示被清除/不存在。"""
        item = self._data.get(key)
        if item is None:
            return True
        if item.expire_at is not None and item.expire_at <= wall_clock:
            del self._data[key]
            self._expired += 1
            return True
        return False

    def _purge_all(self, wall_clock):
        expired_keys = [
            k for k, v in self._data.items()
            if v.expire_at is not None and v.expire_at <= wall_clock
        ]
        for k in expired_keys:
            del self._data[k]
        self._expired += len(expired_keys)
        return len(expired_keys)

    # ---------------- 公开 API ----------------

    def put(self, key, value, ttl=None, expire_at=None):
        """写入键。ttl 为秒数（可为小数），None 表示永不过期。

        expire_at 用于重放：直接给定绝对过期时刻。
        返回写入时的绝对过期时刻（None = 永不过期）。
        """
        with self._lock:
            wall_clock = time.time()
            if expire_at is None and ttl is not None:
                expire_at = wall_clock + max(0.0, float(ttl))
            self._data[key] = StoredValue(value, expire_at)
            self._append({
                "op": "put",
                "key": key,
                "value": value,
                "expire_at": expire_at,
            })
            return expire_at

    def get(self, key):
        """读取。返回 (found, value)；不存在或已过期返回 (False, None)。"""
        with self._lock:
            wall_clock = time.time()
            if self._purge_key(key, wall_clock):
                return False, None
            return True, self._data[key].value

    def delete(self, key):
        """删除。返回 True=删除成功，False=不存在或已过期。"""
        with self._lock:
            wall_clock = time.time()
            if self._purge_key(key, wall_clock):
                return False
            del self._data[key]
            self._append({"op": "delete", "key": key})
            return True

    def incr(self, key, by=1):
        """自增。返回 (status, value)，status in {"ok","not_int"}。

        键不存在按 0 起算；原值不是整数返回 not_int，不修改状态、不写 WAL。
        参与 incr 的键保持原来的过期策略不变。
        """
        with self._lock:
            wall_clock = time.time()
            expire_at = None
            if not self._purge_key(key, wall_clock):
                item = self._data[key]
                cur = item.value
                if not isinstance(cur, int) or isinstance(cur, bool):
                    return "not_int", None
                expire_at = item.expire_at
            new_value = cur + by if not self._is_absent(key) else by
            self._data[key] = StoredValue(new_value, expire_at)
            self._append({
                "op": "incr",
                "key": key,
                "value": new_value,
                "expire_at": expire_at,
            })
            return "ok", new_value

    def _is_absent(self, key):
        return key not in self._data

    def stats(self):
        """返回 (count, expired, uptime_ms)。

        count  = 当前未过期键数（调用前先惰性清除全部过期键）
        expired= 累计因过期被清除的键数
        uptime = 进程已运行毫秒（自本对象创建起）
        """
        with self._lock:
            wall_clock = time.time()
            self._purge_all(wall_clock)
            uptime_ms = int((time.monotonic() - self._start) * 1000)
            return len(self._data), self._expired, uptime_ms

    def close(self):
        with self._lock:
            if self._wal is not None:
                self._wal.flush()
                self._wal.close()
                self._wal = None
