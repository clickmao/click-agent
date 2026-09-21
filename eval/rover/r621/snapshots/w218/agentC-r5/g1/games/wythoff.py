_MAX = 40


def _cold_pairs(limit):
    pairs = set()
    seen = set()
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5) / 2) + 1e-9
        p = int(p)
        while p in seen:
            p += 1
        q = p + i
        pairs.add((p, q))
        seen.add(p)
        seen.add(q)
        if p > limit:
            break
        i += 1
    return pairs


_COLD = _cold_pairs(_MAX)


def _is_cold(a, b):
    return ((a, b) if a <= b else (b, a)) in _COLD


def solve(text):
    toks = text.split()
    if len(toks) < 2:
        return ''
    a, b = int(toks[0]), int(toks[1])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _is_cold(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
