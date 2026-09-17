"""Wythoff's game: lexicographically smallest winning move.

Legal moves take (i, j) stones: i == 0 or j == 0 (one pile only), or
i == j > 0 (equal amounts from both piles).

The P-positions of Wythoff's game are the pairs (floor(n*phi), floor(n*phi^2)),
n >= 0, in either order.  They are produced here by the standard mex
construction, which is exact for the small ranges used by this task.
"""

# Losing (a, b) pairs with 0 <= a, b <= 25, built by the mex rule:
# each new pair uses the smallest unused numbers, and its difference grows by 1.
_LOSING = set()
_used = set()
_diff = 0
while True:
    lo = 0
    while lo in _used:
        lo += 1
    hi = lo + _diff
    if hi > 25:
        break
    _LOSING.update({(lo, hi), (hi, lo)})
    _used.update({lo, hi})
    _diff += 1
_LOSING.add((0, 0))
_LOSING = frozenset(_LOSING)


def _is_losing(a: int, b: int) -> bool:
    """True if (a, b) is a P-position (previous player wins)."""
    return (a, b) in _LOSING


def _candidates(a: int, b: int):
    """All legal moves in lexicographic order."""
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                yield i, j


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])

    if _is_losing(a, b):
        return "LOSE"
    for i, j in _candidates(a, b):
        if _is_losing(a - i, b - j):
            return "WIN %d %d" % (i, j)
    return "LOSE"
