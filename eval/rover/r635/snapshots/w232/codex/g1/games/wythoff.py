"""Wythoff's game: report the lexicographically smallest winning move."""

LIMIT = 30


def _cold_pairs(limit: int):
    """Return the set of losing positions (P-positions) up to `limit`."""
    cold = set()
    used = set()
    x = 0
    for idx in range(limit + 1):
        while x in used:
            x += 1
        y = x + idx
        cold.add((x, y))
        cold.add((y, x))
        used.add(x)
        used.add(y)
        x += 1
    return cold


COLD = _cold_pairs(LIMIT)


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])

    if (a, b) in COLD:
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in COLD:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
