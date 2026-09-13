
class TtlCache:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self._d = capacity, ttl, {}

    def get(self, key, now):
        it = self._d.get(key)
        if it is None:
            return None
        value, t0, _ = it
        if now >= t0 + self.ttl:
            del self._d[key]
            return None
        self._d[key] = (value, t0, now)      # 用 now 当次序 (相同 now 无法区分先后)
        return value

    def put(self, key, value, now):
        self._d.pop(key, None)
        self._d[key] = (value, now, now)
        active = [k for k, (v, t0, _s) in self._d.items() if now < t0 + self.ttl]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._d[k][2])
            del self._d[victim]
            active.remove(victim)
