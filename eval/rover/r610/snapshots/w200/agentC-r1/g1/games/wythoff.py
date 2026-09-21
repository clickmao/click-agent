"""Wythoff game: LOSE or WIN i j (lexicographically smallest winning move)."""
from math import isqrt


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    k = b - a
    n = (isqrt(5 * k * k) + k) // 2
    return a == n


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split())
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
