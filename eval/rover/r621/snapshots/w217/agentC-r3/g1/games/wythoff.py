def _is_lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = int(d * ((5 ** 0.5) + 1) / 2)
    for cand in (x - 1, x, x + 1, x + 2):
        if cand >= 0 and cand * (cand + d) == a * (a + d) and a == cand:
            return True
    return False


def solve(text: str) -> str:
    tok = []
    for ln in text.split('\n'):
        tok.extend(ln.split())
    it = iter(tok)
    a0 = int(next(it))
    b0 = int(next(it))
    best = None
    for i in range(a0 + 1):
        for j in range(b0 + 1):
            if i == 0 and j == 0:
                continue
            single = (i == 0) != (j == 0)
            both = (i != 0 and j != 0 and i == j)
            if not (single or both):
                continue
            if _is_lose(a0 - i, b0 - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
