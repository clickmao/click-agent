"""Wythoff's game: losing-position test and lexicographically smallest move.

Cold (P-)positions are exactly (floor(m*phi), floor(m*phi)+m), m = 0,1,2,...
with phi = (1+sqrt(5))/2.  Inputs are bounded by 25, so we build the exact
table once with integer arithmetic (no float rounding anywhere).
"""


def _isqrt(n: int) -> int:
    if n <= 0:
        return 0
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def _floor_phi(m: int) -> int:
    """Exact floor(m * (1+sqrt(5))/2) for m >= 0 (integer-only).

    m*phi = m/2 + m*sqrt(5)/2; m*sqrt(5) = sqrt(5*m*m).
    floor(m*phi) = floor((m + floor(sqrt(5*m*m))) / 2)  when 5*m*m is not a
    perfect square (always true for m >= 1); m == 0 gives 0 directly.
    """
    if m == 0:
        return 0
    return (m + _isqrt(5 * m * m)) // 2


def _build_cold(limit: int):
    cold = {(0, 0)}
    m = 1
    while True:
        lo = _floor_phi(m)
        hi = lo + m
        if lo > limit and hi > limit:
            break
        cold.add((lo, hi))
        m += 1
    return frozenset(cold)


_COLD = _build_cold(25)


def _cold(a: int, b: int) -> bool:
    return (min(a, b), max(a, b)) in _COLD


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    if _cold(a, b):
        return "LOSE"

    best = None
    # Legal moves: (i) drain one pile, or (ii) drain equal amounts from both.
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            is_equal = i == j
            is_single = (i == 0) != (j == 0)
            if not (is_equal or is_single):
                continue
            if _cold(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
