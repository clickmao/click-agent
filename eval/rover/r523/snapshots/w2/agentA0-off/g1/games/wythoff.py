"""Wythoff's game: take from one pile or equal amounts from both.

Losing positions (for the player to move) are the cold pairs
(floor(n*phi), floor(n*phi^2)) with phi = (1+sqrt(5))/2.
"""

import math

_PHI = (1 + 5 ** 0.5) / 2


def _is_losing(a: int, b: int) -> bool:
    """True if (a, b) is a cold (previous-player-win) position."""
    if a > b:
        a, b = b, a
    n = b - a
    f1 = int(math.floor(n * _PHI))
    f2 = f1 + n
    return (f1, f2) == (a, b)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    if _is_losing(a, b):
        return "LOSE"

    # Collect every winning move, then pick the lexicographically smallest
    # (i, j) with i = amount from pile 1, j = amount from pile 2.
    cand = []
    for i in range(1, a + 1):          # from pile 1 only
        if _is_losing(a - i, b):
            cand.append((i, 0))
    for j in range(1, b + 1):          # from pile 2 only
        if _is_losing(a, b - j):
            cand.append((0, j))
    for d in range(1, min(a, b) + 1):  # equal amounts from both
        if _is_losing(a - d, b - d):
            cand.append((d, d))

    best = min(cand)
    return "WIN %d %d" % (best[0], best[1])
