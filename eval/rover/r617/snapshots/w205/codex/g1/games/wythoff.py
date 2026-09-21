"""Wythoff's game: remove from one pile, or equal amounts from both piles."""


def _is_cold(a, b):
    """True if (a, b) is a losing (cold) position."""
    if a > b:
        a, b = b, a
    n = b - a
    return a == (n * 1618033988749895) // 1000000000000000


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if _is_cold(a, b):
        return "LOSE"

    best = None
    for i in range(1, a + 1):
        if _is_cold(a - i, b) and (best is None or (i, 0) < best):
            best = (i, 0)
    for j in range(1, b + 1):
        if _is_cold(a, b - j) and (best is None or (0, j) < best):
            best = (0, j)
    for t in range(1, min(a, b) + 1):
        if _is_cold(a - t, b - t) and (best is None or (t, t) < best):
            best = (t, t)

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
