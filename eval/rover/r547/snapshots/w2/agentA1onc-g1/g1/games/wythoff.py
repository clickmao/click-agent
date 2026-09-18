"""Wythoff's game: report LOSE, or the lexicographically smallest winning move.

Moves: take any positive number from one pile, or the same positive number
from both piles.  The player taking the last stone wins.

The losing positions are (floor(k*phi), floor(k*phi*phi)) and mirrors.  The
answer is produced by a search over all legal moves, so ties are broken by
plain lexicographic order as required.
"""

from math import isqrt


def _is_losing(a: int, b: int) -> bool:
    """True iff position (a, b) is a loss for the player to move."""
    if a > b:
        a, b = b, a
    # P-position iff (a, b) == (floor(k*phi), floor(k*phi*phi)).
    # b - a == k for such pairs, so k is determined by the difference.
    k = b - a
    # Compute floor(k*phi) without floating point error using integer sqrt:
    # floor(k*phi) == (k*(1+sqrt(5))/2) -> floor((k + floor(k*sqrt(5)))/2)
    # More robust: floor(k * (1 + sqrt(5)) / 2)
    phi_num = k + isqrt(5 * k * k)
    x = phi_num // 2
    y = x + k
    return a == x and b == y


def _gen_moves(a: int, b: int):
    """Yield all legal moves as (i, j) tuples, i, j >= 0."""
    for i in range(1, a + 1):
        yield (i, 0)
    for j in range(1, b + 1):
        yield (0, j)
    for t in range(1, min(a, b) + 1):
        yield (t, t)


def solve(text: str) -> str:
    """Return ``LOSE`` or ``WIN i j`` with lexicographically smallest (i, j)."""
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    for i, j in _gen_moves(a, b):
        if _is_losing(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    return "WIN %d %d" % best
