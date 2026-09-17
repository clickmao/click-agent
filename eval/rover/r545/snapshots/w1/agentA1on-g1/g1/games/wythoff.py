"""Wythoff game: P-position check + lexicographically smallest winning move.
Pure function solve(text) -> str (no trailing newline).
"""


def _losing_points(limit):
    """Set of (a,b) cold (P) positions with a<=b<=limit (Beatty sequences)."""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    pts = set()
    n = 0
    while True:
        a = int(phi * n) if n > 0 else 0
        b = a + n
        if a > limit and b > limit:
            break
        pts.add((a, b))
        if n > 0:
            pts.add((b, a))
        n += 1
        if n > 4 * limit + 10:
            break
    return pts


def solve(text: str) -> str:
    vals = [int(x) for x in text.split()]
    a, b = vals[0], vals[1]
    loss = _losing_points(max(a, b))
    norm = (min(a, b), max(a, b))
    as_set = set()
    for p in loss:
        as_set.add((min(p[0], p[1]), max(p[0], p[1])))
    if norm in as_set:
        return "LOSE"
    # enumerate candidate moves (i,j): i taken from pile a, j from pile b.
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # legal: single pile or equal from both
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            key = (min(na, nb), max(na, nb))
            if key in as_set:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
