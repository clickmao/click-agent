"""Wythoff's game: lexicographically smallest winning move (i, j)."""


def _cold(a: int, b: int) -> bool:
    """True iff (a, b) is a P-position (cold) for Wythoff's game."""
    lo, hi = (a, b) if a <= b else (b, a)
    r = hi - lo
    import math
    # Beatty sequences: cold pairs are (floor(phi*m), floor(phi*phi*m)) for m >= 0
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    m = int(lo / phi + 0.5)
    return lo == int(math.floor(phi * m)) and hi == lo + m


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    # try all candidate moves in lexicographic order of (i, j)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                continue
            if i != j and i != 0 and j != 0:
                continue
            # valid move: either single-pile removal or equal removal from both
            if not (i == 0 or j == 0 or i == j):
                continue
            if _cold(na, nb):
                return "WIN %d %d" % (i, j)
    return "LOSE"
