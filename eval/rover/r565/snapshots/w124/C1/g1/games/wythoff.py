def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    sys_ = _system()

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if sys_[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best


_cache = None


def _system():
    global _cache
    if _cache is None:
        _cache = [[None] * 26 for _ in range(26)]
        for i in range(26):
            for j in range(26):
                _cache[i][j] = _is_reduced(i, j)
    return _cache


def _is_reduced(a: int, b: int) -> bool:
    if a == 0 and b == 0:
        return True
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _reduce_check(a - i, b - j):
                return False
    return True


def _reduce_check(a: int, b: int) -> bool:
    if a == 0 and b == 0:
        return True
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    return x == int(d * 1.618033988749895)
