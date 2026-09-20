import math


LIMIT = 40


def _cold():
    # Wythoff losing (cold) positions: (floor(n*phi), floor(n*phi^2)), n >= 0
    phi = (1 + math.isqrt(5)) / 2
    seen = set()
    res = []
    # generate by scanning mex-style on max coordinate to avoid float issues
    used = [False] * (2 * LIMIT + 2)
    n = 0
    while True:
        a = 0
        while a <= 2 * LIMIT and used[a]:
            a += 1
        if a > 2 * LIMIT:
            break
        b = a + n
        if b > 2 * LIMIT:
            break
        used[a] = True
        used[b] = True
        res.append((a, b))
        n += 1
    return res


COLD = _cold()
COLD_SET = set(COLD)


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    return (a, b) in COLD_SET


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    # rule (i): take from one pile
    for na in range(0, a + 1):
        for nb in (b,):
            pass
    for na in range(0, a + 1):
        i = a - na
        for nb in range(0, b + 1):
            j = b - nb
            if i == 0 and j == 0:
                continue
            one = (i == 0) or (j == 0)
            both = (i == j) and i > 0
            if not (one or both):
                continue
            if _is_cold(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN {0} {1}'.format(best[0], best[1])
