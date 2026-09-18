"""Wythoff's game: decide and give the lexicographically smallest winning move."""


def is_losing(a, b):
    x, y = min(a, b), max(a, b)
    # losing positions are (floor(n*phi), floor(n*phi*phi)) for n >= 0
    # a position is losing iff floor((y - x) * phi) == x
    d = y - x
    # integer check: floor(d * phi) == x  <=>  x <= d*phi < x+1
    # use integer square-root trick to test without floating point carefully
    # d*phi = d * (1 + sqrt(5)) / 2
    # equivalent integer condition (Beatty): floor(d*phi) == x
    # floor((d + d*sqrt5)/2) == x  <=> d + d*sqrt5 in [2x, 2x+2)
    # use isqrt on 5*d*d
    # simpler: compute floor(d*phi) via integer arithmetic
    s = 5 * d * d
    # floor(d*sqrt5) = isqrt(s) (approx, adjust)
    import math
    r = math.isqrt(s)
    while (r + 1) * (r + 1) <= s:
        r += 1
    while r * r > s:
        r -= 1
    # floor(d*phi) = d + floor(d*sqrt5) when d + d*sqrt5 even handling:
    # d*phi = (d + d*sqrt5)/2 -> floor = (d + floor(d*sqrt5)) // 2
    val = (d + r) // 2
    return val == x


def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])

    if is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j == 0:
                pass
            elif i == 0 and j > 0:
                pass
            else:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
