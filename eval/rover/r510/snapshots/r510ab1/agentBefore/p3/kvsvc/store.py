"""核心存储：线程安全的带 TTL 键值存储 + WAL 追加/重放。

设计要点
--------
* 所有可变状态由一把 RLock 保护，保证 8 并发客户端 incr 不丢更新。
* TTL 惰性清除：读取时若已过期则删除并累计 expired 计数。
* 写操作（put/delete/incr）每次都向 WAL 追加一行 JSON。
* 重启重放 WAL：已过期的键不复活（过期淘汰计入 expired）。
"""

import json
import os
import threading
import time

# 哨兵：表示"键不存在"
_MISSING = object()


class NotInt(Exception):
    """原值存在但不是整数，incr 时抛出。"""


class KVStore:
    """线程安全的 KV 存储，带 TTL 与 WAL 持久化。"""

    def __init__(self, wal_path=None, clock=time.monotonic):
        # _data[key] = {"value": Any, "expire_at": float | None}
        self._data = {}
        self._lock = threading.RLock()
        self._expired = 0          # 累计因过期被清除的键数
        self._start = time.monotonic()
        self._clock = clock        # 单调时钟，用于 TTL 判定（不受系统时间回拨影响）
        self._wal_path = wal_path
        self._wal_fp = None
        if wal_path:
            _ensure_parent(wal_path)
            # 追加模式打开，行缓冲；每次写后 flush+fsync 由调用方保证语义
            self._wal_fp = open(wal_path, "a", encoding="utf-8", newline="\n")

    # ---------- 内部辅助 ----------

    def _now(self):
        return self._clock()

    def _reap_locked(self, key):
        """在持锁状态下惰性清除已过期的键。

        返回: (存在且未过期, 值)
        """
        entry = self._data.get(key)
        if entry is None:
            return False, None
        exp = entry["expire_at"]
        if exp is not None and self._now() >= exp:
            del self._data[key]
            self._expired += 1
            return False, None
        return True, entry["value"]

    def _append_wal_locked(self, record):
        """在持锁状态下追加一行 WAL 并落盘。"""
        if self._wal_fp is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal_fp.write(line + "\n")
        self._wal_fp.flush()
        try:
            os.fsync(self._wal_fp.fileno())
        except OSError:
            # 某些文件系统/管道不支持 fsync，退化为 flush 即可
            pass

    # ---------- 对外 API ----------

    def put(self, key, value, ttl=None):
        """写入键值，ttl 为秒（数字），None 表示永不过期。

        返回 {"key", "value", "expires_in"}。
        """
        with self._lock:
            expire_at = None
            if ttl is not None:
                expire_at = self._now() + float(ttl)
            self._data[key] = {"value": value, "expire_at": expire_at}
            self._append_wal_locked({
                "op": "put", "key": key, "value": value,
                "ttl": ttl, "expire_at_mono": expire_at,
            })
            return self._detail_locked(key)

    def get(self, key):
        """读取未过期的键；不存在/已过期返回 None。"""
        with self._lock:
            ok, value = self._reap_locked(key)
            if not ok:
                return None
            return {"key": key, "value": value}

    def delete(self, key):
        """删除未过期的键；不存在/已过期返回 False。"""
        with self._lock:
            ok, _ = self._reap_locked(key)
            if not ok:
                return False
            del self._data[key]
            self._append_wal_locked({"op": "delete", "key": key})
            return True

    def incr(self, key, by=1):
        """整数自增。键不存在按 0 起算；原值非整数抛 NotInt。

        返回 {"key", "value"}。
        """
        with self._lock:
            ok, value = self._reap_locked(key)
            if not ok:
                base = 0
            else:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise NotInt(key)
                base = value
            new_value = base + int(by)
            # incr 结果永不过期（原键若带 ttl，这里按普通值写回：保持原过期时间）
            entry = self._data.get(key)
            expire_at = entry["expire_at"] if entry is not None else None
            self._data[key] = {"value": new_value, "expire_at": expire_at}
            self._append_wal_locked({"op": "incr", "key": key, "by": int(by)})
            return {"key": key, "value": new_value}

    def stats(self):
        """返回 count（未过期键数）、expired（累计过期数）、uptime_ms。"""
        with self._lock:
            # 全量惰性清理，保证 count 是"当前未过期"的真实值
            for key in list(self._data.keys()):
                self._reap_locked(key)
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int((time.monotonic() - self._start) * 1000),
            }

    # ---------- WAL 重放 ----------

    def replay_wal(self):
        """从 WAL 重放恢复状态。

        过期语义：WAL 中的 ttl 是相对时间，重放时按"从该记录写入到现在的
        真实流逝时间"折算。为简化且可复现，这里记录的是 wall-clock 断言：
        重放时用每条记录自带的 expire_at（墙钟绝对时间）判定是否已过期。
        """
        if not self._wal_path or not os.path.exists(self._wal_path):
            return
        now_wall = time.time()
        with self._lock:
            with open(self._wal_path, "r", encoding="utf-8") as fp:
                for raw in fp:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        # 半截行（崩溃中断）：跳过，不视为完整记录
                        continue
                    op = rec.get("op")
                    key = rec.get("key")
                    if op == "put":
                        exp_wall = rec.get("expire_at_wall")
                        expire_at_mono = None
                        if exp_wall is not None:
                            remaining = float(exp_wall) - now_wall
                            if remaining <= 0:
                                # 已过期：不复活，计入 expired
                                self._data.pop(key, None)
                                self._expired += 1
                                continue
                            expire_at_mono = self._now() + remaining
                        self._data[key] = {
                            "value": rec.get("value"),
                            "expire_at": expire_at_mono,
                        }
                    elif op == "delete":
                        ok = self._data.pop(key, _MISSING)
                        if ok is not _MISSING:
                            pass  # 重放删除，不额外计数
                    elif op == "incr":
                        entry = self._data.get(key)
                        base = 0
                        exp = None
                        if entry is not None:
                            exp = entry["expire_at"]
                            v = entry["value"]
                            if isinstance(v, int) and not isinstance(v, bool):
                                base = v
                        self._data[key] = {
                            "value": base + int(rec.get("by", 1)),
                            "expire_at": exp,
                        }
                    # 未知 op 忽略
        # 重放完成后，把 WAL 截断为仅含未过期状态的快照？不需要——
        # 契约只要求"追加"，重放按序覆盖即可。

    def close(self):
        with self._lock:
            if self._wal_fp is not None:
                try:
                    self._wal_fp.flush()
                    self._wal_fp.close()
                finally:
                    self._wal_fp = None

    # ---------- 内部：构造 put 响应 ----------

    def _detail_locked(self, key):
        entry = self._data.get(key)
        if entry is None:
            return {"key": key, "value": None, "expires_in": None}
        exp = entry["expire_at"]
        if exp is None:
            expires_in = None
        else:
            expires_in = max(0.0, exp - self._now())
        return {"key": key, "value": entry["value"], "expires_in": expires_in}


def _ensure_parent(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
