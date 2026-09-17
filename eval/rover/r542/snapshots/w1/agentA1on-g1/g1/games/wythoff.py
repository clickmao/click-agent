"""Wythoff's game: take from one pile (any positive amount) or from both piles
the same positive amount. Whoever takes the last stone wins.

stdin:  one line "a b" (stones in pile 1 and pile 2).
stdout: "LOSE" if the first player loses; otherwise "WIN i j" where (i, j) is
        the lexicographically smallest (i first, then j) winning move,
        i, j >= 0 and not both 0.

Losing positions are exactly (floor(t*phi), floor(t*phi^2)) and swaps, t >= 0.
"""

_PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _is_cold(a: int, b: int) -> bool:
    """True iff (a, b) is a P-position (losing for the player to move)."""
    if a > b:
        a, b = b, a
    # b - a == t determines the candidate Beatty pair; verify by closed form
    # plus an exact float-tolerance guard (small inputs, exact check is cheap).
    t = b - a
    ta = int(t * _PHI)
    hmm = int(t * _PHI * _PHI)
    if a == ta and b == hmm:
        return True
    # exact fallback via integer Beatty computation (t*phi = t + (t*5)//... )
    return False


def _cold_exact(a: int, b: int) -> bool:
    """Exact integer test for a Wythoff P-position (no floating point)."""
    if a > b:
        a, b = b, a
    t = b - a
    # floor(t*phi) = t + floor(t/phi); compute floor(t*phi) with integer sqrt
    # floor(t*phi) = (t + isqrt(5*t*t)) // 2
    from math import isqrt
    fa = (t + isqrt(5 * t * t)) // 2
    if fa != a:
        return False
    # second coordinate must be fa + t
    return b == fa + t


def solve(text: str) -> str:
    """Pure function: full stdin text -> full stdout text (no trailing newline)."""
    lines = text.splitlines()
    if not lines:
        return ""
    a, b = (int(x) for x in lines[0].split())

    if _cold_exact(a, b):
        return "LOSE"

    best = None
    # Move type (i): from pile 1 only.
    for i in range(1, a + 1):
        if _cold_exact(a - i, b):
            best = (i, 0)
            break
    # Move type (i): from pile 2 only.
    if best is None:
        for j in range(1, b + 1):
            if _cold_exact(a, b - j):
                best = (0, j)
                break
    # Move type (ii): same amount k from both piles.
    if best is None:
        k = 1
        while k <= a and k <= b:
            if _cold_exact(a - k, b - k):
                best = (k, k)
                break
            k += 1

    if best is None:
        return "LOSE"  # unreachable: every non-P position has a move to a P one
    return "WIN %d %d" % best
