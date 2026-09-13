
class TtlCache:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self._d, self._seq = capacity, ttl, {}, 0

    def _bump(self):
        self._seq += 1
        return self._seq

    def get(self, key, now):
        it = self._d.get(key)
        if it is None:
            return None
        value, t0, _ = it
        if now > t0 + self.ttl:              # off-by-one: 边界时刻当成未过期
            del self._d[key]
            return None
        self._d[key] = (value, t0, self._bump())
        return value

    def put(self, key, value, now):
        self._d.pop(key, None)
        self._d[key] = (value, now, self._bump())
        active = [k for k, (v, t0, _s) in self._d.items() if now < t0 + self.ttl]
        while len(active) > self.capacity:
            victim = min(active, key=lambda k: self._d[k][2])
            del self._d[victim]
            active.remove(victim)
