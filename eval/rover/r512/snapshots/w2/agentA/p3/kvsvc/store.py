"""存储核心: 线程安全 + TTL 惰性过期 + WAL 追加持久化与重放。

设计要点
--------
* 每个键是一条记录: ``[value, expire_at]``。``expire_at is None`` 表示永不过期。
* 所有公共操作都在同一把 ``threading.RLock`` 下完成 —— 读改写是原子的,
  因此并发 incr 不会丢更新 (契约第 5 条)。
* 惰性过期: 每次访问某键时若已过期, 就删除并累计 ``expired``。
  ``stats()`` 会做一次全局清扫, 使 ``count`` 与 ``expired`` 在无任何请求时也准确。
* WAL: 每次写(put/delete/incr)成功前先同步追加一行 JSON 到 WAL 文件并 flush;
  只写**生效过**的写操作。delete 只在该键当前可见时才落盘,
  这样重放时不会把"对不存在键的 delete"重放成真实的删除。

WAL 行格式(每个写操作一行 JSON, 至少含 "op" 与 "key"):
    {"op":"put",   "key":..., "value":..., "expire_at": <epoch 秒|None>, "ts":...}
    {"op":"delete","key":..., "ts":...}
    {"op":"incr",  "key":..., "by": <整数>, "expire_at": <epoch 秒|None>, "ts":...}

重放后按"当前逻辑时间"求值: 已过期的键不回填(不复活)。
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, List, Optional, Tuple

WAL_FILENAME = "kv.wal"

# 记录类型: (value, expire_at)  expire_at 为 None 表示永不过期
_Record = Tuple[Any, Optional[float]]


class KVStore:
    """带 TTL 与 WAL 的线程安全键值存储。"""

    def __init__(self, wal_path: Optional[str] = None, clock: Callable[[], float] = time.time) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, _Record] = {}
        self._expired = 0
        self._wal_path = os.path.abspath(wal_path) if wal_path else None
        self._wall_clock = clock          # 墙钟, 用于 TTL 与 WAL 时间戳
        self._mono = time.monotonic      # 单调钟, 用于 uptime_ms
        if self._wal_path:
            parent = os.path.dirname(self._wal_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._replay(self._wal_path)

    # ---------------------------------------------------------------- 时间

    def _now(self) -> float:
        return self._wall_clock()

    def _is_alive(self, rec: _Record, now: float) -> bool:
        expire_at = rec[1]
        return expire_at is None or expire_at > now

    def _purge_one(self, key: str, now: float) -> None:
        """若键存在且已过期则清除并计数(调用方须持锁)。"""
        rec = self._data.get(key)
        if rec is not None and not self._is_alive(rec, now):
            del self._data[key]
            self._expired += 1

    def _purge_all(self, now: float) -> None:
        for key in list(self._data):
            self._purge_one(key, now)

    # ---------------------------------------------------------------- WAL

    def _wal_append(self, obj: dict) -> None:
        if not self._wal_path:
            return
        line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
        with open(self._wal_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def _replay(self, path: str) -> None:
        """从 WAL 重放, 恢复未过期的键。已过期的不复活。"""
        if not os.path.exists(path):
            return
        now = self._now()
        data: dict[str, _Record] = {}
        expired = 0
        with open(path, "r", encoding="utf-8-sig") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue  # 容忍尾部截断/脏行
                op = rec.get("op")
                key = rec.get("key")
                if not isinstance(key, str):
                    continue
                if op == "put":
                    data[key] = (rec.get("value"), rec.get("expire_at"))
                elif op == "delete":
                    if key in data:
                        del data[key]
                elif op == "incr":
                    cur, exp = data.get(key, (0, rec.get("expire_at")))
                    if not isinstance(cur, int) or isinstance(cur, bool):
                        cur = 0
                    data[key] = (cur + int(rec.get("by", 1)), rec.get("expire_at", exp))
                # 其它 op: 忽略, 保持前向兼容
        # 求值: 过滤掉重放时已过期的记录
        for key in list(data):
            if not self._is_alive(data[key], now):
                del data[key]
                expired += 1
        self._data = data
        self._expired = expired

    # ---------------------------------------------------------------- 读写

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> dict:
        with self._lock:
            now = self._now()
            self._purge_one(key, now)
            expire_at = (now + float(ttl)) if ttl is not None else None
            self._data[key] = (value, expire_at)
            self._wal_append({
                "op": "put", "key": key, "value": value,
                "expire_at": expire_at, "ts": now,
            })
            return {
                "key": key,
                "value": value,
                "expires_in": (expire_at - now) if expire_at is not None else None,
            }

    def get(self, key: str) -> dict:
        with self._lock:
            now = self._now()
            self._purge_one(key, now)
            rec = self._data.get(key)
            if rec is None:
                return {"key": key, "value": None, "found": False}
            return {"key": key, "value": rec[0], "found": True}

    def delete(self, key: str) -> dict:
        with self._lock:
            now = self._now()
            self._purge_one(key, now)
            existed = key in self._data
            if existed:
                del self._data[key]
                self._wal_append({"op": "delete", "key": key, "ts": now})
            return {"key": key, "deleted": existed}

    def incr(self, key: str, by: int = 1) -> dict:
        """按键做整数自增。原值不是整数 -> not_int; 键不存在按 0 起算。"""
        with self._lock:
            now = self._now()
            self._purge_one(key, now)
            rec = self._data.get(key)
            if rec is None:
                cur, expire_at = 0, None
            else:
                cur, expire_at = rec
                if isinstance(cur, bool) or not isinstance(cur, int):
                    return {"key": key, "value": None, "not_int": True}
            new_val = cur + int(by)
            self._data[key] = (new_val, expire_at)
            self._wal_append({
                "op": "incr", "key": key, "by": int(by),
                "expire_at": expire_at, "ts": now,
            })
            return {"key": key, "value": new_val, "not_int": False}

    def stats(self) -> dict:
        with self._lock:
            self._purge_all(self._now())
            return {
                "count": len(self._data),
                "expired": self._expired,
                "uptime_ms": int(self._mono() * 1000),
            }

    # ---------------------------------------------------------------- 自检

    def _selftest(self) -> List[str]:
        """返回失败信息列表, 空列表 = 全部通过。"""
        failures: List[str] = []
        t = [1000.0]

        def clock() -> float:
            return t[0]

        # 1) 基本 put/get/delete
        s = KVStore(wal_path=None, clock=clock)
        r = s.put("a", {"x": 1})
        if r["expires_in"] is not None:
            failures.append("no-ttl expires_in 应为 None")
        if s.get("a") != {"key": "a", "value": {"x": 1}, "found": True}:
            failures.append("get 无法取回刚写入的值")
        if s.delete("a") != {"key": "a", "deleted": True}:
            failures.append("delete 应返回 deleted=True")
        if s.delete("a")["deleted"] is not False:
            failures.append("删除不存在的键应返回 deleted=False")
        if s.get("a")["found"]:
            failures.append("删除后 get 不应命中")

        # 2) TTL 过期 + 计数
        s = KVStore(wal_path=None, clock=clock)
        s.put("t", 1, ttl=5.0)
        t[0] += 4.9
        if not s.get("t")["found"]:
            failures.append("TTL 未到期时不应过期")
        t[0] += 0.2
        if s.get("t")["found"]:
            failures.append("TTL 到期后键应不可见")
        st = s.stats()
        if st["count"] != 0 or st["expired"] != 1:
            failures.append(f"过期计数错误: {st}")

        # 3) incr 语义
        s = KVStore(wal_path=None, clock=clock)
        if s.incr("c")["value"] != 1:
            failures.append("incr 缺省按 0 起算失败")
        s.incr("c", 9)
        if s.incr("c", 0)["value"] != 10:
            failures.append("incr 累加值不对")
        s.put("s", "str")
        if not s.incr("s")["not_int"]:
            failures.append("非整数原值应判 not_int")

        # 4) 并发 incr 不丢更新
        import threading as _th
        s = KVStore(wal_path=None, clock=clock)
        def worker() -> None:
            for _ in range(200):
                s.incr("n", 1)
        threads = [_th.Thread(target=worker) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        if s.get("n")["value"] != 1600:
            failures.append(f"并发 incr 丢更新: {s.get('n')['value']} != 1600")

        # 5) WAL 重放: 未过期恢复、自增累计、已过期不复活
        s = KVStore(wal_path=None, clock=clock)
        s.put("keep", "v", ttl=100.0)
        s.incr("keep_inc", 5)
        s.incr("keep_inc", 7)
        s.put("short", 1, ttl=2.0)
        s.put("del", 1)
        s.delete("del")

        # 用临时文件验证重放
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".wal")
        os.close(fd)
        os.remove(path)
        try:
            s2 = KVStore(wal_path=path, clock=clock)
            s2.put("keep", "v", ttl=100.0)
            s2.put("gone", 1, ttl=3.0)
            s2.incr("keep_inc", 5)
            s2.incr("keep_inc", 7)
            s2.put("del", 1)
            s2.delete("del")
            t[0] += 5.0  # 越过 gone 的 TTL 与 keep 的 100s 内
            s3 = KVStore(wal_path=path, clock=clock)
            if s3.get("keep") != {"key": "keep", "value": "v", "found": True}:
                failures.append("重放未恢复未过期键")
            if s3.get("keep_inc")["value"] != 12:
                failures.append(f"重放 incr 累计错误: {s3.get('keep_inc')}")
            if s3.get("gone")["found"]:
                failures.append("已过期键在重放后复活")
            if s3.get("del")["found"]:
                failures.append("已删除键在重放后复活")
        finally:
            if os.path.exists(path):
                os.remove(path)

        # 6) WAL 行含 op/key 字段
        fd, path = tempfile.mkstemp(suffix=".wal")
        os.close(fd)
        os.remove(path)
        try:
            s4 = KVStore(wal_path=path, clock=clock)
            s4.put("k1", 1)
            s4.incr("k1", 2)
            s4.delete("k1")
            with open(path, "r", encoding="utf-8") as fh:
                lines = [json.loads(x) for x in fh if x.strip()]
            ops = [r["op"] for r in lines]
            if ops != ["put", "incr", "delete"]:
                failures.append(f"WAL op 序列错误: {ops}")
            if any("key" not in r for r in lines):
                failures.append("WAL 行缺少 key 字段")
        finally:
            if os.path.exists(path):
                os.remove(path)

        return failures
