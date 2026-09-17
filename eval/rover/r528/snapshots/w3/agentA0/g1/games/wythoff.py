"""Wythoff's game. Remove from one pile, or same positive amount from both.

Input: a b.
Output: 'LOSE' for a cold (P-)position, else 'WIN i j' with the lexicographically
smallest winning move (compare i then j; i, j >= 0, not both zero).
"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    lo, hi = (a, b) if a <= b else (b, a)
    # Position is a P-position iff (lo, hi) is a cold pair:
    #   lo == int((hi - lo) * phi), phi = golden ratio.
    d = hi - lo
    cold_lo = int(d * (1 + 5 ** 0.5) / 2)
    if lo == cold_lo:
        return 'LOSE'
    # Enumerate candidate moves; pick lexicographically smallest winning one.
    best = None
    # type (i): remove i from pile 1 only (pile 2 unchanged)
    for i in range(1, a + 1):
        na, nb = a - i, b
        if _is_p(na, nb):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # type (i): remove j from pile 2 only (pile 1 unchanged)
    for j in range(1, b + 1):
        na, nb = a, b - j
        if _is_p(na, nb):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # type (ii): remove t from both piles
    for t in range(1, min(a, b) + 1):
        na, nb = a - t, b - t
        if _is_p(na, nb):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best


def _is_p(x, y):
    lo, hi = (x, y) if x <= y else (y, x)
    return lo == int((hi - lo) * (1 + 5 ** 0.5) / 2)
