"""带 TTL 的键值存储核心: 线程安全 + WAL 追加 + 重启重放。

设计要点:
  * 单一 RLock 保护 (data, expiries, deleted, expired_cleared) —— incr 的
    "读-改-写" 必须原子, 否则并发丢更新 (契约 5)。
  * TTL 惰性清除: 读取/统计时才判定过期, 过期即从 data 移除并累加
    expired_cleared (契约 4)。
  * WAL 每行一个 JSON 对象, 至少含 op / key。op ∈ {put, delete, incr}。
    put 记录写入时刻的 expires_at 绝对时间 (不是 ttl), 这样重放时无需
    重新计时, 未过期恢复、已过期丢弃 (契约 6)。
  * 重放只信任绝对时间戳, 因此重启后过期键不会复活。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Optional

# WAL 记录的操作类型白名单 (契约 6 要求 op 取值必须是这三者之一)
_OP_PUT = "put"
_OP_DELETE = "delete"
_OP_INCR = "incr"
_VALID_OPS = frozenset({_OP_PUT, _OP_DELETE, _OP_INCR})


class KVStore:
    """线程安全、可持久化、带过期时间的键值存储。

    :param wal_path: WAL 文件路径; 服务启动时若存在则重放。
    """

    def __init__(self, wal_path: str) -> None:
        # 数据平面: key -> 原始 JSON 值 (put 的值, 或 incr 产生的 int)
        self._data: dict[str, Any] = {}
        # 过期平面: key -> 绝对过期时间 (time.monotonic 无关, 用 time.time 以便 WAL 复用)
        self._expires_at: dict[str, float] = {}
        # 累计统计
        self._expired_cleared: int = 0
        self._lock = threading.RLock()

        self._wal_path = wal_path
        self._wal_fp = None

        # 确保 WAL 目录存在 (显式处理, 不假设 cwd)
        wal_dir = os.path.dirname(os.path.abspath(wal_path))
        if wal_dir:
            os.makedirs(wal_dir, exist_ok=True)

        self._replay_wal()
        # 以追加模式打开, 行缓冲关闭 -> 由 _append_wal 显式 flush
        self._wal_fp = open(self._wal_path, "a", encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------ WAL

    def _replay_wal(self) -> None:
        """启动时重放 WAL。只接受合法 op; 已过期的 put 不复活。"""
        if not os.path.exists(self._wal_path):
            return
        now = time.time()
        with open(self._wal_path, "r", encoding="utf-8-sig") as fp:
            for raw in fp:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, TypeError):
                    # 半截行 (进程被 kill) 或损坏行: 跳过, 不因 WAL 污点拒绝启动
                    continue
                if not isinstance(rec, dict):
                    continue
                op = rec.get("op")
                key = rec.get("key")
                if op not in _VALID_OPS or not isinstance(key, str):
                    continue
                if op == _OP_PUT:
                    exp = rec.get("expires_at")
                    if exp is not None and not isinstance(exp, (int, float)):
                        continue
                    # 已过期的 put 不得复活 (契约 6)
                    if exp is not None and float(exp) <= now:
                        self._expired_cleared += 1
                        self._data.pop(key, None)
                        self._expires_at.pop(key, None)
                        continue
                    self._data[key] = rec.get("value")
                    if exp is None:
                        self._expires_at.pop(key, None)
                    else:
                        self._expires_at[key] = float(exp)
                elif op == _OP_DELETE:
                    self._data.pop(key, None)
                    self._expires_at.pop(key, None)
                elif op == _OP_INCR:
                    by = rec.get("by", 1)
                    if not isinstance(by, int) or isinstance(by, bool):
                        continue
                    cur = self._data.get(key, 0)
                    if not isinstance(cur, int) or isinstance(cur, bool):
                        cur = 0
                    self._data[key] = cur + by

    def _append_wal(self, rec: dict) -> None:
        """追加一行 WAL 并 flush。调用方必须已持锁。"""
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        self._wal_fp.write(line + "\n")
        self._wal_fp.flush()
        try:
            os.fsync(self._wal_fp.fileno())
        except OSError:
            # 某些文件系统/容器不支持 fsync: 降级为仅 flush, 不阻断写路径
            pass

    # ------------------------------------------------------------- 过期清理

    def _purge_expired_locked(self, key: Optional[str] = None) -> None:
        """惰性清除。key=None 时扫描全部键; 否则只查该键。调用方须持锁。"""
        now = time.time()
        if key is None:
            expired = [k for k, exp in self._expires_at.items() if exp <= now]
        else:
            exp = self._expires_at.get(key)
            expired = [key] if exp is not None and exp <= now else []
        for k in expired:
            self._data.pop(k, None)
            self._expires_at.pop(k, None)
            self._expired_cleared += 1

    # --------------------------------------------------------------- 读写 API

    def put(self, key: str, value: Any, ttl: Optional[float]) -> dict:
        """写入键值。ttl 为 None 表示永不过期。返回含 expires_in 的响应体。"""
        with self._lock:
            self._purge_expired_locked(key)
            if ttl is None:
                expires_at = None
            else:
                expires_at = time.time() + float(ttl)
            self._data[key] = value
            if expires_at is None:
                self._expires_at.pop(key, None)
            else:
                self._expires_at[key] = expires_at
            self._append_wal(
                {_OP_PUT and "op": _OP_PUT, "key": key, "value": value,
                 "expires_at": expires_at}
            )
            return {
                "key": key,
                "value": value,
                "expires_in": None if expires_at is None else max(0.0, expires_at - time.time()),
            }

    def get(self, key: str):
        """读取。不存在或已过期返回 None。"""
        with self._lock:
            self._purge_expired_locked(key)
            if key not in self._data:
                return None
            return {"key": key, "value": self._data[key]}

    def delete(self, key: str) -> bool:
        """删除。键不存在或已过期返回 False。"""
        with self._lock:
            self._purge_expired_locked(key)
            if key not in self._data:
                return False
            self._data.pop(key, None)
            self._expires_at.pop(key, None)
            self._append_wal({"op": _OP_DELETE, "key": key})
            return True

    def incr(self, key: str, by: int):
        """整数自增。键不存在按 0 起算; 原值非 int 返回 ("not_int", None)。"""
        with self._lock:
            # 读-改-写在同一把锁内完成, 并发不丢更新 (契约 5)
            self._purge_expired_locked(key)
            cur = self._data.get(key, 0)
            if isinstance(cur, bool) or not isinstance(cur, int):
                return "not_int", None
            new = cur + by
            self._data[key] = new
            self._append_wal({"op": _OP_INCR, "key": key, "by": by})
            return "ok", {"key": key, "value": new}

    def stats(self) -> dict:
        """统计: 当前未过期键数 / 累计过期清除数 / 进程运行毫秒。"""
        with self._lock:
            self._purge_expired_locked(None)
            return {
                "count": len(self._data),
                "expired": self._expired_cleared,
            }

    def close(self) -> None:
        with self._lock:
            if self._wal_fp is not None:
                try:
                    self._wal_fp.close()
                finally:
                    self._wal_fp = None
