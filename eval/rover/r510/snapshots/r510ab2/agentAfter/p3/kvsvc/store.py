"""带过期时间的键值存储 + WAL 持久化（仅标准库）。

设计要点
--------
* KVStore 内部只保存「未过期」语义：读取/删除时惰性清除已过期条目。
* 每次写操作（put/delete/incr）先落 WAL（append + flush + fsync），再改内存。
* 重放时按 WAL 顺序重建；重放到某条记录时若该记录自身的 expire_at 已过，
  则不复活该键（老键也不因此复活 —— 因为老键的 expire_at 早于新记录，
  而记录按时间递增写入，故只需丢弃该记录即可，见 replay() 注释）。
* 并发正确性：所有状态变更在同一把 threading.RLock 下完成，
  incr 的「读-改-写」是临界区，不会丢更新。
"""

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# WAL 中 op 字段的合法取值（契约 6）
OP_PUT = "put"
OP_DELETE = "delete"
OP_INCR = "incr"
_VALID_OPS = (OP_PUT, OP_DELETE, OP_INCR)


class KVStore:
    """带过期时间与 WAL 的键值存储。线程安全。"""

    def __init__(self, wal_path: str) -> None:
        self._wal_path = wal_path
        self._lock = threading.RLock()
        # key -> (value, expire_at or None)  ; expire_at 为绝对 time.monotonic 基准
        self._data: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._expired_count = 0  # 累计因过期被清除的键数（契约 3 stats.expired）
        # WAL 文件：目录可能不存在，显式创建
        d = os.path.dirname(os.path.abspath(wal_path))
        if d:
            os.makedirs(d, exist_ok=True)
        # 打开为文本 "a"，UTF-8，newline="\n" 保证跨平台换行一致（基线：换行显式处理）
        self._wal = open(wal_path, "a", encoding="utf-8", newline="\n")
        self._replay(wal_path)

    # ---------------- 内部：WAL ----------------

    def _wal_append(self, obj: Dict[str, Any]) -> None:
        """把一条操作记录追加为一行 JSON 并落盘。调用方须持锁。"""
        line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        self._wal.write(line + "\n")
        self._wal.flush()
        os.fsync(self._wal.fileno())

    def _replay(self, wal_path: str) -> None:
        """从 WAL 重放，恢复未过期的键值（含 incr 累计值）。"""
        if not os.path.exists(wal_path):
            return
        # 以「读到 EOF 时」的墙钟为基准，把记录里的相对 ttl 折算成 monotonic 绝对时间。
        # 记录里持久化的是 expire_at_wall（epoch 秒），因此可跨重启直接比较。
        now_wall = time.time()
        with open(wal_path, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, TypeError):
                    continue  # 半截行 / 损坏行：跳过（append-only 尾部可能被截断）
                op = rec.get("op")
                key = rec.get("key")
                if not isinstance(key, str) or op not in _VALID_OPS:
                    continue
                exp_wall = rec.get("expire_at")  # epoch 秒 或 null
                alive = (exp_wall is None) or (float(exp_wall) > now_wall)
                if op == OP_PUT:
                    if not alive:
                        # 已过期的 put：不复活；同时抹掉此前可能存在的同名键
                        self._data.pop(key, None)
                        continue
                    self._data[key] = (rec.get("value"), exp_wall)
                elif op == OP_DELETE:
                    self._data.pop(key, None)
                elif op == OP_INCR:
                    if not alive:
                        continue
                    cur = self._data.get(key)
                    base = cur[0] if (cur is not None and isinstance(cur[0], int)
                                      and not isinstance(cur[0], bool)) else 0
                    new_exp = exp_wall if exp_wall is not None else (cur[1] if cur else None)
                    if not alive:
                        continue
                    self._data[key] = (base + int(rec.get("by", 1)), new_exp)

    # ---------------- 内部：过期 ----------------

    @staticmethod
    def _to_wall(ttl: Optional[float]) -> Optional[float]:
        if ttl is None:
            return None
        return time.time() + float(ttl)

    def _live(self, key: str) -> Optional[Tuple[Any, Optional[float]]]:
        """返回未过期条目；若不存在或已过期则返回 None（惰性清除并计数）。须持锁。"""
        ent = self._data.get(key)
        if ent is None:
            return None
        value, exp_wall = ent
        if exp_wall is not None and float(exp_wall) <= time.time():
            del self._data[key]
            self._expired_count += 1
            return None
        return ent

    def _sweep(self) -> int:
        """清理所有已过期键，返回本次清除数（用于 stats 的 count 精确性）。须持锁。"""
        now = time.time()
        dead = [k for k, (_v, e) in self._data.items()
                if e is not None and float(e) <= now]
        for k in dead:
            del self._data[k]
            self._expired_count += 1
        return len(dead)

    # ---------------- 公开 API ----------------

    def put(self, key: str, value: Any, ttl: Optional[float]) -> Optional[float]:
        """写入键值。ttl 为秒（None=永不过期）。

        返回剩余秒数（ttl 为 None 时返回 None）。返回 None 也可表示无 ttl。
        """
        with self._lock:
            exp_wall = self._to_wall(ttl)
            self._wal_append({
                "op": OP_PUT, "key": key, "value": value, "expire_at": exp_wall,
            })
            self._data[key] = (value, exp_wall)
            if ttl is None:
                return None
            return float(ttl)

    def get(self, key: str) -> Optional[Tuple[Any, Any]]:
        """返回 (value, expires_in)；不存在/已过期返回 None。"""
        with self._lock:
            ent = self._live(key)
            if ent is None:
                return None
            value, exp_wall = ent
            if exp_wall is None:
                return value, None
            return value, max(0.0, float(exp_wall) - time.time())

    def delete(self, key: str) -> bool:
        """删除键。存在且未过期返回 True，否则 False。"""
        with self._lock:
            if self._live(key) is None:
                return False
            self._wal_append({"op": OP_DELETE, "key": key})
            del self._data[key]
            return True

    def incr(self, key: str, by: int) -> Tuple[bool, int]:
        """整数自增。返回 (ok, value)；原值非整数返回 (False, 0)。

        键不存在按 0 起算；沿用原键的过期时间（若存在）。
        """
        with self._lock:
            ent = self._live(key)
            if ent is None:
                base = 0
                exp_wall = None
            else:
                base_val, exp_wall = ent
                if isinstance(base_val, bool) or not isinstance(base_val, int):
                    return False, 0
                base = base_val
            new_val = base + int(by)
            self._wal_append({
                "op": OP_INCR, "key": key, "by": int(by), "value": new_val,
                "expire_at": exp_wall,
            })
            self._data[key] = (new_val, exp_wall)
            return True, new_val

    def stats(self) -> Dict[str, int]:
        """返回 count（未过期键数）/ expired（累计过期清除数）。

        uptime_ms 由 server 层按进程启动时间计算，不在此处。
        """
        with self._lock:
            self._sweep()
            return {"count": len(self._data), "expired": self._expired_count}

    def close(self) -> None:
        with self._lock:
            try:
                self._wal.flush()
                self._wal.close()
            except Exception:
                pass
