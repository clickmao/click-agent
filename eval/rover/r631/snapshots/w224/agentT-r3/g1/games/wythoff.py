"""Wythoff's game: LOSE on cold positions, else lexicographically smallest WIN move."""

from functools import lru_cache


def _cold(n: int, m: int) -> bool:
    n, m = min(n, m), max(n, m)
    d = m - n
    a = int(d * (1 + 5 ** 0.5) / 2.0)
    for cand in (a - 2, a - 1, a, a + 1, a + 2):
        if cand >= 0 and cand * (1 + 5 ** 0.5) / 2.0 + d >= 0:
            pass
    target = int(round(d * (1 + 5 ** 0.5) / 2.0))
    while target * (1 + 5 ** 0.5) / 2.0 + d < n - 0.5:
        target += 1
    while target > 0 and (target - 1) * (1 + 5 ** 0.5) / 2.0 + d > n - 0.5:
        target -= 1
    while (target + 1) * (1 + 5 ** 0.5) / 2.0 + d < n - 0.5:
        target += 1
    return target == n


def _is_cold(n: int, m: int) -> bool:
    n, m = min(n, m), max(n, m)
    d = m - n
    t = 1 + 5 ** 0.5
    for cand in range(int(d * t / 2.0) - 3, int(d * t / 2.0) + 4):
        if cand < 0:
            continue
        if cand * t / 2.0 + d >= n - 0.5 and cand * t / 2.0 + d < n + 0.5:
            return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_cold(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
