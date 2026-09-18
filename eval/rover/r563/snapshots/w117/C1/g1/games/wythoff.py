def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lo, hi = min(a, b), max(a, b)
    # losing positions are (floor(m*phi), floor(m*phi^2))
    import math
    phi = (1 + math.sqrt(5)) / 2
    is_lose = False
    m = int(hi / phi) + 2
    for t in range(1, m + 1):
        p = int(t * phi)
        q = int(t * phi * phi)
        if p > 25 or q > 25:
            break
        if p == lo and q == hi:
            is_lose = True
            break
    if is_lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i != 0 and j != 0 and i != j:
                continue
            if (na, nb) in _losing_set():
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best


def _losing_set():
    import math
    phi = (1 + math.sqrt(5)) / 2
    res = set()
    for t in range(1, 40):
        p = int(t * phi)
        q = int(t * phi * phi)
        if p > 25 and q > 25:
            break
        for x, y in ((p, q), (q, p)):
            if x <= 25 and y <= 25:
                res.add((x, y))
        res.add((0, 0))
    return res
