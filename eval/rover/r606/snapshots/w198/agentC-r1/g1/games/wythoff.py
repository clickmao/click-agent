"""Wythoff 博弈必败点判定。"""

from math import isqrt


def _lose_pair(x: int, y: int):
    """判定 (x, y) 是否为必败点（不区分两堆次序）。"""
    a, b = (x, y) if x <= y else (y, x)
    d = b - a
    n = (isqrt(5 * d * d) + d) // 2
    for cand in (n - 2, n - 1, n, n + 1, n + 2):
        if cand < 0:
            continue
        if (cand + d, cand) == (a, b):
            return True
    return False


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _lose_pair(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if _lose_pair(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
