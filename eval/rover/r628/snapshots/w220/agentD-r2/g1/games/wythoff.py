"""Wythoff game: LOSE if cold position, else WIN i j lexicographically smallest."""


def _cold(a, b):
    """True if (a, b) is a Wythoff cold (P) position."""
    if a > b:
        a, b = b, a
    # cold positions: (floor(t*phi), floor(t*phi*phi)) for t >= 0
    import math
    phi = (1 + math.sqrt(5)) / 2
    t = int(a / phi)
    for cand in (t - 1, t, t + 1):
        if cand < 0:
            continue
        ca = int(math.floor(cand * phi))
        cb = int(math.floor(cand * phi * phi))
        if ca == a and cb == b:
            return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    # option (i): remove from a single pile
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j > 0:
                continue
            na, nb = a - i, b - j
            if _cold(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
