"""Wythoff's game: lexicographically smallest winning move."""


def _losing(a: int, b: int) -> bool:
    """A position is losing for the player to move iff (a,b) is a
    Wythoff pair: (floor(n*phi), floor(n*phi)+n)."""
    if a > b:
        a, b = b, a
    # Losing positions have b - a = n = b - floor(n*phi).  Test candidates
    # around the index inferred from the difference, using exact integers
    # so rounding can never flip the result.
    n = b - a
    for cand in (n - 1, n, n + 1):
        if cand < 0:
            continue
        # floor(cand * phi) computed exactly via the recurrence-free formula.
        x = _floor_mul_phi(cand)
        if x == a and x + cand == b:
            return True
    return False


def _floor_mul_phi(n: int) -> int:
    """Exact floor(n * (1+sqrt(5))/2) using integer square root."""
    if n == 0:
        return 0
    return (n + _isqrt(5 * n * n)) // 2


def _isqrt(x: int) -> int:
    r = int(x ** 0.5)
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) <= x:
        r += 1
    return r


def solve(text: str) -> str:
    a, b = map(int, text.split())

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            # A move takes i from pile 1 and j from pile 2; it is legal only
            # if it affects a single pile, or takes equal amounts from both.
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(na, nb):
                return "WIN %d %d" % (i, j)
    return "LOSE"
