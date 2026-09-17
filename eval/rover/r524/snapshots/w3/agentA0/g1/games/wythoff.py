"""Wythoff's game: decide win/lose and the lexicographically smallest winning move.

Input text layout (the whole stdin):
    one line: a b   (1<=a<=25, 1<=b<=25 stones in the two piles)

Play: two players alternate; a move is either
    (i)  remove any positive number from exactly one pile, or
    (ii) remove the same positive number from both piles.
Whoever takes the last stone wins.

Output:
    first player loses -> "LOSE"
    otherwise          -> "WIN i j"  (take i from pile 1, j from pile 2; i,j>=0,
                                      not both zero; (i,j) lexicographically smallest
                                      over all winning moves)
No trailing newline.
"""

__all__ = ["solve"]

# Golden-ratio based characterisation of the P-positions (Wythoff pairs):
#   (a_n, b_n) = (floor(n*phi), floor(n*phi^2)),  n >= 1, with a_n = b_n - n.
# A position (x, y), x <= y, is losing iff x == floor((y - x) * phi).
_PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _is_losing(x: int, y: int) -> bool:
    """True iff (x, y) is a P-position (previous player wins, i.e. mover loses)."""
    if x > y:
        x, y = y, x
    d = y - x
    if d == 0:
        return x == 0
    lo = int(d * _PHI)
    # Guard against floating rounding near integer boundaries.
    for cand in (lo - 1, lo, lo + 1):
        if cand >= 0 and cand == x - 0:
            return x == cand
    return x == lo


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    # Enumerate moves in lexicographic order of (i, j); return the first move
    # that leaves a P-position for the opponent.
    # Legal (i, j): i>0,j==0 (from pile1); i==0,j>0 (from pile2); i==j>0 (both).
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
