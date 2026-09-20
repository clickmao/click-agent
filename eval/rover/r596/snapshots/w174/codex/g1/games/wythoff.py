"""Wythoff's game: lexicographically smallest winning move."""

from fractions import Fraction


def _is_losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    # Wythoff pairs: (floor(d*phi), floor(d*phi)+d), phi = (1+sqrt5)/2.
    # Use a high-precision rational approximation (safe for d <= 25).
    phi = Fraction(1618033989, 1000000000)
    p = (d * phi).__floor__()
    return lo == p and hi == p + d


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    if _is_losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)

    return "LOSE"
