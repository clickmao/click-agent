"""kvsvc.store —— 线程安全的带 TTL 键值存储 + WAL 追加/重放。

设计要点:
- 所有状态变更在单把可重入锁内完成 (原子的"过期判定 + 写入 + WAL 追加")，
  保证多线程 incr 不丢更新 (契约 5)。
- 惰性过期: 读/写路径都会先清理命中键; 另提供 sweep() 供 stats 统计。
- WAL: 每次 put/delete/incr 追加一行 JSON, 至少含 op / key 字段 (契约 6)。
  重放时只应用带绝对过期时刻的行, 已过期键不复活。
- 重放期间处于 "replaying" 模式: 不重复追加 WAL。
"""

import json
import os
import threading
import time

__all__ = ["KVStore"]

_ABSENT = object()


class KVStore:
    def __init__(self, wal_path, clock=time.time):
        self._wal_path = os.path.abspath(wal_path)
        self._clock = clock
        self._lock = threading.RLock()
        # key -> [value, expires_at(绝对时刻 float) 或 None]
        self._data = {}
        self._expired_count = 0
        self._replaying = False
        self._wal_fh = None
        self._open_wal()
        self.replay()

    # ---------- WAL 底层 ----------
    def _open_wal(self):
        parent = os.path.dirname(self._wal_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # 追加模式 + UTF-8; 每次写入后 flush, 保证重启可读到。
        self._wal_fh = open(self._wal_path, "a", encoding="utf-8", newline="\n")

    def _append_wal(self, op, key, **extra):
        if self._replaying:
            return
        rec = {"op": op, "key": key}
        rec.update(extra)
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        self._wal_fh.write(line + "\n")
        self._wal_fh.flush()

    def close(self):
        with self._lock:
            if self._wal_fh is not None:
                try:
                    self._wal_fh.flush()
                    self._wal_fh.close()
                finally:
                    self._wal_fh = None

    # ---------- 过期处理 ----------
    def _purge_locked(self, key, now):
        """调用方必须持锁。返回内层记录或 _ABSENT。"""
        rec = self._data.get(key)
        if rec is None:
            return _ABSENT
        exp = rec[1]
        if exp is not None and exp <= now:
            del self._data[key]
            self._expired_count += 1
            return _ABSENT
        return rec

    def sweep(self):
        """主动清理所有已过期键; 返回本次清理数量。"""
        now = self._clock()
        with self._lock:
            dead = [
                k
                for k, rec in self._data.items()
                if rec[1] is not None and rec[1] <= now
            ]
            for k in dead:
                del self._data[k]
            self._expired_count += len(dead)
            return len(dead)

    # ---------- 对外操作 ----------
    def put(self, key, value, ttl):
        now = self._clock()
        if ttl is None:
            expires_at = None
        else:
            expires_at = now + float(ttl)
        with self._lock:
            self._purge_locked(key, now)
            self._data[key] = [value, expires_at]
            self._append_wal("put", key, value=value, expires_at=expires_at)
            remaining = None if expires_at is None else max(0.0, expires_at - now)
            return {"key": key, "value": value, "expires_in": remaining}

    def get(self, key):
        now = self._clock()
        with self._lock:
            rec = self._purge_locked(key, now)
            if rec is _ABSENT:
                return None
            return {"key": key, "value": rec[0]}

    def delete(self, key):
        now = self._clock()
        with self._lock:
            rec = self._purge_locked(key, now)
            if rec is _ABSENT:
                return False
            del self._data[key]
            self._append_wal("delete", key)
            return True

    def incr(self, key, by, ttl=None):
        """整数自增; 键不存在按 0 起算; 原值非整数 -> ValueError('not_int')。"""
        now = self._clock()
        if isinstance(by, bool) or not isinstance(by, int):
            raise ValueError("not_int")
        with self._lock:
            rec = self._purge_locked(key, now)
            if rec is _ABSENT:
                cur = 0
                expires_at = None if ttl is None else now + float(ttl)
            else:
                cur = rec[0]
                expires_at = rec[1]
                if isinstance(cur, bool) or not isinstance(cur, int):
                    raise ValueError("not_int")
            newval = cur + by
            self._data[key] = [newval, expires_at]
            # 记下累计值, 使重放不依赖 by 语义也能恢复整数。
            self._append_wal("incr", key, by=by, value=newval, expires_at=expires_at)
            return {"key": key, "value": newval}

    def stats(self):
        now = self._clock()
        with self._lock:
            dead = [
                k
                for k, rec in self._data.items()
                if rec[1] is not None and rec[1] <= now
            ]
            for k in dead:
                del self._data[k]
            self._expired_count += len(dead)
            return {"count": len(self._data), "expired": self._expired_count}

    # ---------- 重放 ----------
    def replay(self):
        """从 WAL 重放; 已过期键不复活。返回应用的有效记录数。"""
        if not os.path.exists(self._wal_path):
            return 0
        applied = 0
        now = self._clock()
        with self._lock:
            self._replaying = True
            try:
                with open(self._wal_path, "r", encoding="utf-8") as fh:
                    for raw in fh:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            rec = json.loads(raw)
                        except (ValueError, TypeError):
                            continue  # 容忍半截行
                        if not isinstance(rec, dict):
                            continue
                        op = rec.get("op")
                        key = rec.get("key")
                        if not isinstance(key, str):
                            continue
                        if op == "put":
                            exp = rec.get("expires_at")
                            if exp is not None and exp <= now:
                                self._expired_count += 1
                                continue
                            self._data[key] = [rec.get("value"), exp]
                            applied += 1
                        elif op == "incr":
                            exp = rec.get("expires_at")
                            if exp is not None and exp <= now:
                                self._expired_count += 1
                                continue
                            # 优先用记录的累计值; 缺失则按 by 累加。
                            if "value" in rec and isinstance(rec["value"], int) \
                                    and not isinstance(rec["value"], bool):
                                newval = rec["value"]
                            else:
                                prev = self._data.get(key)
                                base = prev[0] if prev and isinstance(prev[0], int) \
                                    and not isinstance(prev[0], bool) else 0
                                newval = base + rec.get("by", 1)
                            self._data[key] = [newval, exp]
                            applied += 1
                        elif op == "delete":
                            self._data.pop(key, None)
                            applied += 1
            finally:
                self._replaying = False
        return applied
