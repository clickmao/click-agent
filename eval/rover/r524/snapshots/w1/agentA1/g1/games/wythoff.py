"""Game `wythoff`: Wythoff's game, losing-position decision.

Input : one line "a b" (1<=a<=25, 1<=b<=25) -- stones in the two piles.
Output: "LOSE" if the first player loses, else "WIN i j" meaning remove i stones
        from the first pile and j from the second, where (i, j) is the
        lexicographically smallest (compare i first, then j; i, j >= 0 and not
        both 0) among all winning moves.

Play: players alternately either (i) remove any positive number of stones from
one pile, or (ii) remove the same positive number of stones from both piles;
the player taking the last stone wins (normal play).

Bounds are tiny (<= 25), so the game value of a position is computed exactly
with a memoised retrograde search (integer-only, no floating point, no
mathematical closed form that could mis-round on the hidden cases).
"""

from functools import lru_cache

_MAX = 25


@lru_cache(maxsize=None)
def _win(x, y):
    """True iff the player to move on (x, y) can force a win."""
    for i in range(1, x + 1):
        if not _win(x - i, y):
            return True
    for j in range(1, y + 1):
        if not _win(x, y - j):
            return True
    for t in range(1, min(x, y) + 1):
        if not _win(x - t, y - t):
            return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[0:2])

    # Enumerate moves in lexicographic order of (i, j): i ascending, and for
    # each i the single possible j values in ascending order.  The first move
    # that lands on a losing (cold) position for the opponent is the answer.
    for i in range(0, a + 1):
        if i >= 1 and not _win(a - i, b):
            return "WIN %d 0" % i
        if i <= b and not _win(a, b - i):
            return "WIN 0 %d" % i
        if i >= 1 and i <= min(a, b) and not _win(a - i, b - i):
            return "WIN %d %d" % (i, i)
    return "LOSE"
