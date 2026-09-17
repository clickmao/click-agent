"""Wythoff's game: (i) remove any positive from one pile, or
(ii) remove the same positive amount from both piles. Last move wins."""

from math import isqrt


def _lose(a: int, b: int) -> bool:
    """True iff (a, b) is a cold (P-)position: a == floor(phi*n),
    b == a + n for some n >= 0 (with a <= b)."""
    if a > b:
        a, b = b, a
    n = b - a
    # Beatty sequence: floor(phi*n) with phi = (1+sqrt(5))/2, exact via
    # m = (n + isqrt(5*n*n)) // 2.
    m = (n + isqrt(5 * n * n)) // 2
    return a == m


def solve(text: str) -> str:
    """Read 'a b'; return 'LOSE' for cold positions, else the
    lexicographically smallest winning move 'WIN i j'."""
    a, b = (int(x) for x in text.split()[:2])
    if _lose(a, b):
        return "LOSE"

    # Enumerate candidate moves; pick lexicographically smallest (i, j).
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # not a legal move
            # legal: single-pile (i>0 xor j>0) or equal both-pile (i==j>0)
            if _lose(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
