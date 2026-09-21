"""Wythoff 博弈：判必败点，否则给字典序最小的 (i, j) 必胜着法。"""


def _losing_set(limit: int = 40):
    y = set()
    for t in range(limit):
        u = int(t * (1 + 5 ** 0.5) / 2 + 1e-9)
        v = u + t
        y.add((u, v))
        y.add((v, u))
    return y


_LOSES = _losing_set()


def _is_lose(x: int, y: int) -> bool:
    if (x, y) in _LOSES:
        return True
    return (y, x) in _LOSES


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        if _is_lose(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if _is_lose(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    for t in range(1, min(a, b) + 1):
        if _is_lose(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
