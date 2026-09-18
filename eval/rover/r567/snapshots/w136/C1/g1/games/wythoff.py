"""Wythoff's game: win/lose plus the lexicographically smallest winning move.

Cold (P-)positions are exactly the pairs (floor(n*phi), floor(n*phi^2))
for n >= 0, i.e. (x, y) = (floor(n*phi), x + n).  Since a, b <= 25 we
enumerate the cold points directly and verify with exact arithmetic.
"""


def _cold_points(limit: int):
    """Return the set of cold positions within [0, limit] x [0, limit]."""
    points = set()
    n = 0
    while True:
        x = (n * 16180339887498948487) // 10 ** 19  # floor(n*phi)
        y = x + n
        if x > limit and y > limit:
            break
        if x <= limit and y <= limit:
            points.add((x, y))
            points.add((y, x))
        n += 1
    return points


_COLD = _cold_points(25)


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split()[:2])

    if (a, b) in _COLD:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if (a - i, b - j) in _COLD:
                return "WIN %d %d" % (i, j)

    return "LOSE"
