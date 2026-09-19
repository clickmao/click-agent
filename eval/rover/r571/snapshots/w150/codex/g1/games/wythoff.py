import math


def _is_losing(a, b):
    """True iff (a, b) is a Wythoff cold (P) position."""
    if a > b:
        a, b = b, a
    n = b - a
    # P-positions are (floor(n*phi), floor(n*phi) + n); with
    # floor(n*phi) = (n + isqrt(5*n*n)) // 2 this stays exact in integers.
    x = (n + math.isqrt(5 * n * n)) // 2
    return x == a and x + n == b


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])

    best = None
    for i in range(1, a + 1):
        if _is_losing(a - i, b):
            if best is None or i < best[0]:
                best = (i, 0)
    for j in range(1, b + 1):
        if _is_losing(a, b - j):
            if best is None or 0 < best[0] or (best[0] == 0 and j < best[1]):
                best = (0, j)
    for k in range(1, min(a, b) + 1):
        if _is_losing(a - k, b - k):
            if best is None or k < best[0]:
                best = (k, k)

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
