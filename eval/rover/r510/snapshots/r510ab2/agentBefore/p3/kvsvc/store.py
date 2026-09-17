"""存储内核。

设计要点:
1. 所有键值操作由一把 ``threading.RLock`` 保护 —— incr 的
   "读-改-写" 必须是一个不可分割的临界区, 否则并发下会丢更新。
2. TTL 采用惰性清除: 读写路径上先检查是否过期, 过期即删除并累加
   ``expired`` 计数; ``count``/``purge_expired`` 提供主动清扫。
3. WAL: 每次写操作(put/delete/incr)在**释放锁之前或之后**追加一行
   JSON, 保证 "值已生效 => 该行已落盘"。重放时按写入顺序回放,
   过期时间点用绝对 epoch 秒记录, 因此重启后已过期的键不会复活。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

__all__ = ["KVStore", "WALError"]


class WALError(RuntimeError):
    """WAL 文件无法打开/追加/解析时抛出。"""


class _Entry:
    """内部条目: 值 + 绝对过期时刻(epoch 秒), None 表示永不过期。"""

    __slots__ = ("value", "expire_at")

    def __init__(self, value: Any, expire_at: Optional[float]) -> None:
        self.value = value
        self.expire_at = expire_at

    def is_expired(self, now: float) -> bool:
        return self.expire_at is not None and now >= self.expire_at


class KVStore:
    """线程安全、带 TTL、带 WAL 持久化的键值存储。"""

    #: 允许出现在 WAL 中的操作名
    OPS = ("put", "delete", "incr")

    def __init__(self, wal_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, _Entry] = {}
        self._expired = 0          # 累计因过期被清除的键数
        self._start = time.monotonic()
        self._wal_path = os.path.abspath(wal_path) if wal_path else None
        self._wal_file = None

        if self._wal_path:
            parent = os.path.dirname(self._wal_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._replay()
            # 以追加模式打开, 行缓冲, UTF-8; 服务生命周期内保持句柄
            self._wal_file = open(
                self._wal_path, "a", encoding="utf-8", newline="\n"
            )

    # ------------------------------------------------------------------ WAL
    def _append_wal(self, op: str, key: str, **extra: Any) -> None:
        """追加一行 WAL。必须在持有锁时调用以保证与内存状态同序。"""
        assert op in self.OPS, op
        if self._wal_file is None:
            return
        record = {"op": op, "key": key}
        record.update(extra)
        line = json.dumps(record, ensure_ascii=False, allow_nan=False)
        try:
            self._wal_file.write(line + "\n")
            self._wal_file.flush()
            os.fsync(self._wal_file.fileno())
        except OSError as exc:  # pragma: no cover - 磁盘/权限异常
            raise WALError(f"WAL 写入失败: {exc}") from exc

    def _replay(self) -> None:
        """从 WAL 重放。坏行跳过(尽力恢复), 已过期条目不回填。"""
        if not self._wal_path or not os.path.exists(self._wal_path):
            return
        now = time.time()
        with open(self._wal_path, "r", encoding="utf-8-sig") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, TypeError):
                    continue  # 截断/损坏行: 跳过, 不让整个服务起不来
                if not isinstance(rec, dict):
                    continue
                self._apply_record(rec, now)

    def _apply_record(self, rec: Dict[str, Any], now: float) -> None:
        """把一条 WAL 记录应用到内存(重放用, 不写 WAL)。"""
        op = rec.get("op")
        key = rec.get("key")
        if op not in self.OPS or not isinstance(key, str):
            return
        raw_exp = rec.get("expire_at")
        expire_at = float(raw_exp) if isinstance(raw_exp, (int, float)) else None

        if op == "delete":
            self._data.pop(key, None)
            return
        if op == "incr":
            delta = rec.get("by")
            base_rec = rec.get("base")
            if not isinstance(delta, int) or isinstance(delta, bool):
                return
            base = base_rec if isinstance(base_rec, int) and not isinstance(base_rec, bool) else 0
            self._data[key] = _Entry(base + delta, expire_at)
            return
        # put
        if expire_at is not None and now >= expire_at:
            return  # 重启时已过期: 不复活
        self._data[key] = _Entry(rec.get("value"), expire_at)

    # ------------------------------------------------------------- 内部工具
    def _get_live_locked(self, key: str, now: float) -> Optional[_Entry]:
        """取未过期条目; 命中过期条目则清除并计数。调用方须持锁。"""
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.is_expired(now):
            del self._data[key]
            self._expired += 1
            return None
        return entry

    def _purge_locked(self, now: float) -> None:
        dead = [k for k, e in self._data.items() if e.is_expired(now)]
        for k in dead:
            del self._data[k]
            self._expired += 1

    # ---------------------------------------------------------------- 公开API
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> Dict[str, Any]:
        """写入键值。ttl 为秒(可小数), None 表示不过期。"""
        if ttl is not None:
            ttl = float(ttl)
            if ttl <= 0:
                # ttl<=0: 立即过期语义 —— 等同于立即删除, 但仍记账
                with self._lock:
                    now = time.time()
                    self._get_live_locked(key, now)  # 顺手清理旧值并计数
                    self._data.pop(key, None)
                    self._append_wal("put", key, value=value, expire_at=now)
                return {"key": key, "value": value, "expires_in": 0.0}
        with self._lock:
            now = time.time()
            expire_at = None if ttl is None else now + float(ttl)
            self._get_live_locked(key, now)  # 覆盖写: 旧值若已过期先计数
            self._data[key] = _Entry(value, expire_at)
            self._append_wal("put", key, value=value, expire_at=expire_at)
            remaining = None if expire_at is None else expire_at - now
        return {"key": key, "value": value, "expires_in": remaining}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """读键。不存在/已过期返回 None。"""
        with self._lock:
            entry = self._get_live_locked(key, time.time())
            if entry is None:
                return None
            return {"key": key, "value": entry.value}

    def delete(self, key: str) -> bool:
        """删除键。不存在/已过期返回 False。"""
        with self._lock:
            now = time.time()
            if self._get_live_locked(key, now) is None:
                return False
            del self._data[key]
            self._append_wal("delete", key)
            return True

    def incr(self, key: str, by: int = 1) -> Dict[str, Any]:
        """原子自增。键不存在按 0 起算; 原值非整数抛 ValueError('not_int')。

        整个 "读-改-写 + WAL 追加" 在同一临界区内完成, 因此并发安全。
        """
        if not isinstance(by, int) or isinstance(by, bool):
            raise ValueError("not_int")
        with self._lock:
            now = time.time()
            entry = self._get_live_locked(key, now)
            if entry is None:
                base, expire_at = 0, None
            else:
                base = entry.value
                if not isinstance(base, int) or isinstance(base, bool):
                    raise ValueError("not_int")
                expire_at = entry.expire_at
            new_value = base + by
            self._data[key] = _Entry(new_value, expire_at)
            # base 入 WAL: 重放时无需依赖插入顺序即可还原该次自增结果
            self._append_wal("incr", key, by=by, base=base, expire_at=expire_at)
            return {"key": key, "value": new_value}

    def stats(self) -> Dict[str, int]:
        """count=未过期键数; expired=累计过期清除数; uptime_ms=运行毫秒。"""
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            count = len(self._data)
            expired = self._expired
        return {
            "count": count,
            "expired": expired,
            "uptime_ms": int((time.monotonic() - self._start) * 1000),
        }

    def keys(self) -> List[str]:
        """当前未过期键列表(测试/调试用)。"""
        with self._lock:
            now = time.time()
            self._purge_locked(now)
            return list(self._data.keys())

    def close(self) -> None:
        with self._lock:
            if self._wal_file is not None:
                try:
                    self._wal_file.flush()
                    self._wal_file.close()
                finally:
                    self._wal_file = None
