# -*- coding: utf-8 -*-
"""本轮程序题的自解: TtlCache (精确过期语义 + 访问先后 LRU)。

规格要点 (逐条对上题面):
 ① 过期: now >= t0 + ttl 即过期 (边界相等也算过期) —— 精确口径, 不是 >。
 ② 最近使用次序 = **访问先后** (内部自增序号), 不能用 now 值代替 (now 可相等)。
 ③ 容量: 活跃条目数 (按当前 now 未过期者) 超过 capacity 时淘汰最久未使用。
"""


class TtlCache:
    def __init__(self, capacity: int, ttl: int):
        self.capacity = capacity
        self.ttl = ttl
        self._items = {}          # key -> [value, inserted_at, recency_seq]
        self._seq = 0

    # ── 内部 ──
    def _touch(self, key):
        self._seq += 1
        self._items[key][2] = self._seq

    def _expired(self, key, now):
        return now >= self._items[key][1] + self.ttl

    def _evict_if_needed(self, now):
        active = [k for k in self._items if not self._expired(k, now)]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._items[k][2])
            del self._items[victim]
            active.remove(victim)

    # ── 对外 ──
    def put(self, key, value, now):
        self._items.pop(key, None)
        self._items[key] = [value, now, 0]
        self._touch(key)
        self._evict_if_needed(now)

    def get(self, key, now):
        item = self._items.get(key)
        if item is None:
            return None
        if self._expired(key, now):
            del self._items[key]
            return None
        self._touch(key)
        return item[0]
