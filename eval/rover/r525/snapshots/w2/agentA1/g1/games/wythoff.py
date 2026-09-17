"""Wythoff's game: decide LOSE or the lexicographically smallest winning move.

solve(text) is pure: text is the complete stdin, the return value is the
complete stdout (no trailing newline).
"""

_PHI = (1 + 5 ** 0.5) / 2.0


def _is_losing(a: int, b: int) -> bool:
    """Return True iff (a, b) is a P-position (player to move loses).

    Wythoff P-positions are exactly (floor(k*phi), floor(k*phi^2)) for k >= 0.
    Normalizing a <= b and letting d = b - a, this is equivalent to:
        d == 0  =>  losing iff a == 0                     (the (0,0) position)
        d >  0  =>  losing iff a == floor(d * phi)
    (the second clause already subsumes d > a, since floor(d*phi) >= d > a when
    d >= 1; there is no extra "d > a" precondition).  Values a, b <= 25 keep
    d*phi far from integer boundaries, so the float evaluation is exact here.
    """
    if a > b:
        a, b = b, a
    d = b - a
    if d == 0:
        return a == 0
    return a == int(d * _PHI)


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    a = int(tokens[0])
    b = int(tokens[1])

    if _is_losing(a, b):
        return "LOSE"

    # Enumerate every legal move (i, j): reduce one pile by any positive amount,
    # or both piles by the same positive amount. Pick the lexicographically
    # smallest (i, j) leading to a losing position for the opponent.
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
