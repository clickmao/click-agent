"""Wythoff 博弈：判定必败点，否则给出字典序最小的必胜着法。"""

import math


def _losing(x, y):
    if x > y:
        x, y = y, x
    d = y - x
    t = math.isqrt(5 * d * d) if hasattr(math, 'isqrt') else int((5 * d * d) ** 0.5)
    n = (d * (1 + 5 ** 0.5)) / 2
    n = int(n)
    for cand in (n - 2, n - 1, n, n + 1, n + 2):
        if cand >= 0 and x == cand:
            return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _losing(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
