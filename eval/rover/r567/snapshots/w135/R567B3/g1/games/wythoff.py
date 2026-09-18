"""Wythoff's game: lose iff (a,b) is a Wythoff pair; else lexicographically
smallest winning move (i, j), i from first pile, j from second, i,j >= 0,
not both zero.

Position is (x, y) = stones remaining in heap1, heap2 after the move.
Initial (a, b) is losing iff it is Wythoff pair (floor(n*phi), floor(n*phi^2)),
n >= 0, which here means a < b, a == floor(n*(sqrt(5)-1)/2) for n = b - a.
"""

from math import isqrt


MAXN = 40
WIDTH = 25


def _wythoff_pairs(maxv=MAXN):
    pairs = set()
    for n in range(maxv + 1):
        x = n * (1 + isqrt(5)) // 2
        y = x + n
        if x > WIDTH + 1 or y > WIDTH + 1:
            break
        pairs.add((x, y))
        pairs.add((y, x))
    return pairs


def _canon(a, b):
    return (a, b) if a <= b else (b, a)


def solve(text: str) -> str:
    a, b = map(int, text.split())
    width = max(a, b)
    pairs = _wythoff_pairs(width)
    losing = set()
    for n in range(0, width + 2):
        x = n * (1 + isqrt(5)) // 2
        y = x + n
        if x > width or y > width:
            break
        losing.add((x, y))
    if _canon(a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if (i != 0 and j != 0 and i != j):
                continue
            if _canon(na, nb) in losing:
                if best is None or (i, j) < (best[0], best[1]):
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
