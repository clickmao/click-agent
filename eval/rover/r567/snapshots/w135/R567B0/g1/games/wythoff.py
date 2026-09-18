_CACHE = None


def _lose_set(limit):
    global _CACHE
    if _CACHE is not None and _CACHE[0] >= limit:
        return _CACHE[1]
    s = {}
    n = 1
    while n <= limit:
        a = (n * (1 + 5 ** 0.5) / 2)
        a = int(a)
        while True:
            b = a + n
            ok = True
            for m in range(1, n):
                pa = int(m * (1 + 5 ** 0.5) / 2)
                if pa == a or pa + m == a or pa == b or pa + m == b:
                    ok = False
                    break
            if ok:
                break
            a += 1
        s[a] = b
        s[b] = a
        n += 1
    _CACHE = (limit, s)
    return s


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    limit = max(a, b)
    pos = _lose_set(limit)
    if pos.get(a) == b:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and (a - i) != (b - j):
                continue
            na, nb = a - i, b - j
            if pos.get(na) == nb:
                key = (i, j)
                if best is None or key < best:
                    best = key
        if best is not None and best[0] == i:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
