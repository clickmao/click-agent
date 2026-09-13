实现类 TtlCache(capacity: int, ttl: int):
- put(key, value, now: int): 写入, now 为逻辑时钟 (单调不减)。
- get(key, now: int): 命中返回 value, 未命中或**已过期**返回 None。
过期语义 (**精确口径**): 记写入时刻 t0, 当 now >= t0 + ttl 即视为过期 (边界相等也算过期);
被 get 命中或 put 覆盖会刷新其"最近使用"次序 —— 次序按**访问先后**判定 (内部自增序号),
不得用 now 值代替 (now 可相等, 相同的 now 不足以确定先后)。
容量: 写入使活跃条目数超过 capacity 时, 淘汰**最久未被使用**的条目 (LRU)。
