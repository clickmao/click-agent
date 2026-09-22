"""Wythoff game: lose-position test and lexicographically smallest winning move."""

# A position (a, b) is losing iff {a, b} == {floor(n*phi), floor(n*phi^2)}
# for n = b - a >= 0.  The Beatty (lower Wythoff) sequence is
# floor(n*phi) = n + floor((n - 1) / phi) ... computed here exactly with
# integer square roots so no floating point error can creep in.


def _isqrt(x):
    if x < 0:
        return -1
    r = int(x ** 0.5)
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) <= x:
        r += 1
    return r


def _phi_num(den):
    """(1 + sqrt(5)) / 2 scaled by den, rounded to nearest integer."""
    return (den + _isqrt(5 * den * den)) // 2


def lower_wythoff(n):
    """Exact floor(n * phi) via integer arithmetic.

    floor(n * phi) = n + floor(n / phi); 1/phi = phi - 1, so
    floor(n / phi) = floor((n * phi_num - n * den) / den) with a
    sufficiently large denominator to make rounding harmless.
    """
    den = 1 << 20
    phi = _phi_num(den)          # ceil-ish scaled phi; fix below
    # refine so that |phi - phi*den| < 1 strictly on the low side
    while (2 * phi + 1) * (2 * phi + 1) < 5 * den * den:
        phi += 1
    while phi * phi > den * den + 5 * den * den // 4:
        phi -= 1
    # now phi*den approximates (1+sqrt(5))/2*den^2?  fall back to exact loop
    lo, hi = n, 2 * n + 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _isqrt(5 * mid * mid) + mid < 2 * n:
            lo = mid
        else:
            hi = mid - 1
    return lo


def is_lose(x, y):
    if x > y:
        x, y = y, x
    n = y - x
    if n < 0:
        return False
    return x == lower_wythoff(n)


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split())

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            if is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
