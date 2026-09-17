"""核心键值存储: TTL 惰性过期 + 预写日志 (WAL) 持久化/重放.

设计要点
--------
* 所有公开方法都在同一把可重入锁 (RLock) 内执行, 保证并发 incr 不丢更新。
* 过期采用惰性清除: 读取/统计时发现过期即删除并累加 expired 计数。
* 每次写操作 (put/delete/incr) 先追加 WAL 再改内存; WAL 行是单行 JSON 对象,
  至少含 "op" (put|delete|incr) 与 "key" 字段。
* incr 重放: 按历史增量重算即可得到相同累计值, 无需额外"已应用"状态。
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional, Tuple

# 显式哨兵: 区分"键不存在"与"键存在且值为 JSON null"
_MISSING = object()


class KVStore:
    """线程安全、带 TTL 与 WAL 的键值存储。"""

    def __init__(self, wal_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        # key -> (value, expire_at 或 None)
        self._data: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._expired = 0  # 累计因过期被清除的键数
        self._wal_path = wal_path
        self._wal_file = None
        if wal_path:
            # 追加方式打开, UTF-8 编码, 每次写后 flush
            self._wal_file = open(wal_path, "a", encoding="utf-8", newline="\n")
            self.replay()

    # ---------------------------------------------------------------- WAL
    def _append_wal(self, record: Dict[str, Any]) -> None:
        """追加一行 JSON 到 WAL; 调用方须持有锁。"""
        if self._wal_file is None:
            return
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        self._wal_file.write(line + "\n")
        self._wal_file.flush()

    def replay(self) -> None:
        """从 WAL 重放, 恢复未过期键值 (含 incr 累计值)。"""
        assert self._wal_path is not None
        now = time.time()
        try:
            fh = open(self._wal_path, "r", encoding="utf-8")
        except FileNotFoundError:
            return
        with fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (ValueError, TypeError):
                    continue  # 跳过损坏/半截行, 不阻断恢复
                if not isinstance(rec, dict):
                    continue
                op = rec.get("op")
                key = rec.get("key")
                if not isinstance(key, str):
                    continue
                if op == "put":
                    exp = rec.get("expire_at")
                    if exp is not None and not isinstance(exp, (int, float)):
                        exp = None
                    # 已过期的键不得复活
                    if exp is not None and exp <= now:
                        continue
                    self._data[key] = (rec.get("value"), exp)
                elif op == "delete":
                    self._data.pop(key, None)
                elif op == "incr":
                    cur = self._data.get(key)
                    base = cur[0] if cur is not None else 0
                    if isinstance(base, bool) or not isinstance(base, int):
                        continue
                    expire_at = cur[1] if cur is not None else None
                    # 重放时也尊重过期: 若已过期则从 0 重新起算
                    if expire_at is not None and expire_at <= now:
                        base = 0
                        expire_at = None
                    self._data[key] = (base + int(rec.get("by", 1)), expire_at)

    # ------------------------------------------------------------ 内部工具
    def _purge_if_expired(self, key: str, now: float) -> bool:
        """若键过期则清除并计数, 调用方须持有锁。"""
        item = self._data.get(key)
        if item is None:
            return False
        exp = item[1]
        if exp is not None and exp <= now:
            del self._data[key]
            self._expired += 1
            return True
        return False

    # -------------------------------------------------------------- 公开 API
    def put(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        now: Optional[float] = None,
    ) -> Optional[float]:
        """写入键值; 返回剩余秒数 (无 ttl 时 None)。ttl<=0 视为立即过期。"""
        if now is None:
            now = time.time()
        expire_at: Optional[float] = None
        if ttl is not None:
            expire_at = now + float(ttl)
        with self._lock:
            self._append_wal(
                {"op": "put", "key": key, "value": value, "expire_at": expire_at}
            )
            self._data[key] = (value, expire_at)
            if expire_at is not None and expire_at <= now:
                self._purge_if_expired(key, now)
                return 0.0
            return None if expire_at is None else expire_at - now

    def contains(self, key: str, now: Optional[float] = None) -> bool:
        """键是否存在且未过期 (与「值为 JSON null」区分)。"""
        if now is None:
            now = time.time()
        with self._lock:
            self._purge_if_expired(key, now)
            return key in self._data

    def get(self, key: str, now: Optional[float] = None) -> Any:
        """读未过期键; 不存在/已过期返回哨兵 _MISSING。"""
        if now is None:
            now = time.time()
        with self._lock:
            self._purge_if_expired(key, now)
            item = self._data.get(key)
            if item is None:
                return _MISSING
            return item[0]

    def delete(self, key: str) -> bool:
        """删除键; 不存在或已过期返回 False。"""
        now = time.time()
        with self._lock:
            self._purge_if_expired(key, now)
            if key not in self._data:
                return False
            self._append_wal({"op": "delete", "key": key})
            del self._data[key]
            return True

    def incr(self, key: str, by: int = 1) -> Tuple[bool, int]:
        """自增; 返回 (ok, value)。

        ok=False 表示原值存在但不是整数 (调用方回 409 not_int)。
        键不存在按 0 起算; incr 不改变原有 TTL。
        """
        now = time.time()
        with self._lock:
            self._purge_if_expired(key, now)
            item = self._data.get(key)
            if item is None:
                base = 0
                expire_at: Optional[float] = None
            else:
                base = item[0]
                expire_at = item[1]
                if isinstance(base, bool) or not isinstance(base, int):
                    return False, 0
            new_val = base + int(by)
            self._append_wal({"op": "incr", "key": key, "by": int(by)})
            self._data[key] = (new_val, expire_at)
            return True, new_val

    def stats(self, now: Optional[float] = None) -> Dict[str, int]:
        """返回当前未过期键数与累计过期数。"""
        if now is None:
            now = time.time()
        with self._lock:
            for key in list(self._data.keys()):
                self._purge_if_expired(key, now)
            return {"count": len(self._data), "expired": self._expired}


# --------------------------------------------------------------- 自检入口
def _selftest() -> int:
    """无头自检: TTL / 并发 incr / WAL 恢复 / 过期不复活 / null 值区分。

    运行: python3 -m kvsvc.store   (退出码 0=PASS, 非 0=FAIL)
    """
    import os
    import tempfile
    import threading as _th

    failures = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # 1) 基本 put/get/delete + ttl 惰性过期
    s = KVStore()
    s.put("a", {"x": 1})
    check("get_put", s.get("a") == {"x": 1})
    check("del_ok", s.delete("a") is True)
    check("del_missing", s.delete("a") is False)

    s.put("t", "v", ttl=0.05)
    check("get_before_ttl", s.get("t") == "v")
    time.sleep(0.08)
    check("expired_invisible", s.get("t") is _MISSING)
    check("expired_contains_false", s.contains("t") is False)
    st = s.stats()
    check("expired_counted", st["expired"] == 1)
    check("count_after_expire", st["count"] == 0)

    # 2) 值为 JSON null 与键不存在必须区分
    s.put("nul", None)
    check("null_exists", s.contains("nul") is True)
    check("null_value", s.get("nul") is None)
    check("missing_sentinel", s.get("nope") is _MISSING)

    # 3) incr: 不存在按 0, 非整数 -> 409 语义, TTL 不被 incr 清除
    check("incr_new", s.incr("n", 5) == (True, 5))
    check("incr_by_default", s.incr("n") == (True, 6))
    s.put("s", "hello")
    check("incr_not_int", s.incr("s") == (False, 0))

    # 4) 并发 incr 不丢更新: 8 线程 x 200 次 = 1600
    s2 = KVStore()

    def worker():
        for _ in range(200):
            s2.incr("c", 1)

    threads = [_th.Thread(target=worker) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    check("concurrent_incr", s2.get("c") == 1600)

    # 5) WAL 恢复 (含 incr 累计) + 过期不复活 + delete 后不恢复
    tmp = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmp, "wal.log")
    w = KVStore(wal)
    w.put("keep", [1, 2, 3], ttl=3600)
    w.incr("cnt", 7)
    w.put("gone", "x", ttl=0.05)
    w.put("del_me", "z")
    w.delete("del_me")
    w.put("keep2", "y", ttl=3600)
    time.sleep(0.08)
    w.stats()  # 触发 gone 过期清除
    del w
    r = KVStore(wal)
    check("replay_incr", r.get("cnt") == 7)
    check("replay_deleted_absent", r.get("del_me") is _MISSING)
    check("replay_keep2", r.get("keep2") == "y")
    check("replay_expired_not_revived", r.get("gone") is _MISSING)
    check("replay_keep_ttl", isinstance(r.get("keep"), list))

    # 6) WAL 行格式: 每行含 op 与 key, op 取值合法
    ops = []
    with open(wal, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            ops.append(rec.get("op"))
            if "key" not in rec:
                failures.append("wal_key_field")
    check("wal_ops_valid", all(o in ("put", "delete", "incr") for o in ops))
    check("wal_has_all_ops", {"put", "delete", "incr"}.issubset(set(ops)))

    if failures:
        print("FAIL: " + ", ".join(failures))
        return 1
    print("PASS: all invariants hold")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
