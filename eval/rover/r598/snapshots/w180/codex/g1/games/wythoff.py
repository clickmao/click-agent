"""Wythoff's game: P-position test and lexicographically smallest winning move."""

# Cold (P) positions are the pairs (floor(n*phi), floor(n*phi^2)).
# Values of a, b are bounded by 25, so the reachable cold positions are
# listed explicitly (exact, no floating point rounding involved).
_COLD = frozenset(
    (a, b) if a <= b else (b, a)
    for a, b in (
        (0, 0), (1, 2), (3, 5), (4, 7), (6, 10), (8, 13), (9, 15),
        (11, 18), (12, 20), (14, 23), (16, 26), (17, 28),
    )
)


def _is_lose(a: int, b: int) -> bool:
    """True if the position (a, b) is a cold (P) position."""
    return (min(a, b), max(a, b)) in _COLD


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if _is_lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
