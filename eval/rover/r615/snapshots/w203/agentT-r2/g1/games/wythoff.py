"""Wythoff game: decide LOSE for losing positions, else lexicographically minimal winning move."""

MAXN = 60


def _build_cold(limit):
    """Return set of losing (P) positions (a, b) with 0 <= a <= b <= limit.

    Losing positions are (floor(m*phi), floor(m*phi^2)) for m >= 0, where
    phi = (1 + sqrt(5)) / 2.  Computed exactly with integer arithmetic to
    avoid floating point error.
    """
    cold = set()
    m = 0
    while True:
        a = (m * 196418 + 121393) // 317811  # floor(m * phi)
        b = a + m
        if a > limit and b > limit:
            break
        if a > limit or b > limit:
            m += 1
            continue
        if a > b:
            a, b = b, a
        cold.add((a, b))
        m += 1
    return cold


_COLD = _build_cold(MAXN)


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    if a < 0 or b < 0:
        return False
    return (a, b) in _COLD


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    # (i) remove from exactly one pile (the other keeps its count)
    for i in range(0, a + 1):
        if _is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if _is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # (ii) remove the same positive amount from both piles
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return "WIN %d %d" % best
