"""Wythoff's game: find the lexicographically smallest winning move."""

_PHI = 1.618033988749895


def _is_losing(x: int, y: int) -> bool:
    """True if (x, y) is a P-position (previous player wins)."""
    if x > y:
        x, y = y, x
    m = y - x
    return x == int(m * _PHI) and y == x + m


def _previous(x: int, y: int):
    """The unique P-position reached from (x, y) by one legal move, if any."""
    best = None
    for i in range(0, x + 1):
        for j in range(0, y + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue  # only legal moves
            if _is_losing(x - i, y - j):
                best = (i, j)
                break
        if best is not None:
            break
    return best


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split())
    if _is_losing(a, b):
        return "LOSE"
    i, j = _previous(a, b)
    return "WIN %d %d" % (i, j)
