from math import isqrt


def _cold(a, b):
    x, y = (a, b) if a <= b else (b, a)
    n = y - x
    t = (isqrt(5 * n * n) + n) // 2
    return x == t


def solve(text):
    a, b = map(int, text.split())
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j):
                if _cold(a - i, b - j):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    i, j = best
    return 'WIN %d %d' % (i, j)
