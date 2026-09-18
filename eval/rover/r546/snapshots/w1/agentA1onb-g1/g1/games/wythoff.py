"""Game ``wythoff``: Wythoff's game, two piles (a, b), 1<=a,b<=25.

stdin:
    line 1:  a b
stdout:
    'LOSE'    first player loses
    'WIN i j' winning move (remove i from pile 1, j from pile 2),
              lexicographically smallest over all winning moves
              (compare i first, then j; i,j >= 0, not both zero)
    no trailing newline.

Moves: (i) remove any positive number from one pile, or
       (ii) remove the same positive number from both piles.
Last stone taken wins.  Losing positions are (floor(n*phi), floor(n*phi^2)).
"""

from __future__ import annotations

PHI = 1.6180339887498948482  # (1 + sqrt(5)) / 2


def _is_losing(a: int, b: int) -> bool:
    """Return True iff (min, max) is a Wythoff cold (losing) position."""
    x, y = (a, b) if a <= b else (b, a)
    if x == y:
        return x == 0
    n = y - x
    # n-th cold position: (floor(n*phi), floor(n*phi^2)) = (u, u + n)
    u = int(n * PHI)
    return x == u and y == u + n


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])
    if _is_losing(a, b):
        return 'LOSE'

    # Enumerate all moves and pick the lexicographically smallest winning one.
    # Candidates ordered by (i, j) lexicographically.
    best = None
    # i from 0..a, j from 0..b  (lex order: outer loop i, inner loop j)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # Legal moves: only one pile, or equal amounts from both piles.
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
