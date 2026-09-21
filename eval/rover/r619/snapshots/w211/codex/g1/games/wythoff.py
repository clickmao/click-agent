"""Wythoff's game: report the lexicographically smallest winning move."""

import math


def _is_losing(x: int, y: int) -> bool:
    lo, hi = (x, y) if x <= y else (y, x)
    phi = (1 + math.sqrt(5)) / 2
    n = (lo + 1) if lo == 0 else int(lo / phi) + 1
    while n > 0:
        low = int(n * phi)
        if low == lo:
            return low + n == hi
        if low < lo:
            return False
        n -= 1
    return lo == 0 and hi == 0


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) != (j == 0):
                ok = True
            else:
                ok = i == j
            if ok and _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
