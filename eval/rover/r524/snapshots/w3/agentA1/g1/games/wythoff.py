"""Wythoff's game: decide the losing positions and the lexicographically
smallest winning move.

Input format:
    a b             (1 <= a <= 25, 1 <= b <= 25)

Moves: (i) remove any positive number from a single pile, or (ii) remove the
same positive number from both piles.  Whoever takes the last stone wins.
Output for a first-player loss (P-position):
    LOSE
Otherwise:
    WIN i j         remove i from the first pile and j from the second,
                    lexicographically smallest (i, j), i,j >= 0, not both 0.

The P-positions of Wythoff's game are the cold positions
(floor(n*phi), floor(n*phi^2)) for n >= 0 together with their reflections.
"""

from math import isqrt


def _is_losing(a: int, b: int) -> bool:
    """True iff (a, b) (unordered) is a Wythoff P-position."""
    if a > b:
        a, b = b, a
    # n = b - a is the candidate cold index; the lower value must equal
    # floor(n * phi) with phi = (1 + sqrt(5)) / 2, computed exactly via
    # floor(n*phi) = (n + isqrt(5*n*n)) // 2.
    n = b - a
    lo = (n + isqrt(5 * n * n)) // 2
    return a == lo


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    a, b = (int(x) for x in lines[0].split())

    if _is_losing(a, b):
        return 'LOSE'

    # Enumerate every legal move and keep the lexicographically smallest one
    # that lands on a P-position.  A move is (i, j): i removed from pile 1,
    # j removed from pile 2; valid if 0<=i<=a, 0<=j<=b, (i,j)!=(0,0), and
    # either i==0, or j==0, or i==j.
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # Legal single-pile or equal-removal move?
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break  # j ascending -> smallest j for this i
        if best is not None:
            break  # i ascending -> smallest i overall
    if best is None:
        return 'LOSE'
    return 'WIN {} {}'.format(best[0], best[1])
