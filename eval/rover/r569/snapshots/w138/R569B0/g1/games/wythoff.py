import math


def _cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    x = (math.isqrt(5 * d * d) + d) // 2
    return a == x and b == a + d


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
