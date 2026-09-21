"""Wythoff's game: take from one pile or equal amounts from both."""

PHI = 1.6180339887498949
PHI2 = 2.6180339887498949


def _losing_pair(n):
    a = int(n * PHI)
    b = int(n * PHI2)
    return a, b


def _is_losing(x, y):
    if x > y:
        x, y = y, x
    cand = int(x / PHI)
    for n in (cand - 2, cand - 1, cand, cand + 1, cand + 2):
        if n < 0:
            continue
        a, b = _losing_pair(n)
        if a == x and b == y:
            return True
    return False


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % (best[0], best[1])
