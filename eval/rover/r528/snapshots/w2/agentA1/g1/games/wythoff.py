"""Wythoff's game: report the lexicographically smallest winning move, or LOSE."""

_COLD_LIMIT = 64
_COLD = set()


def _build_cold(limit):
    """Generate cold (P-)positions via the Beatty sequences floor(n*phi), floor(n*phi^2)."""
    phi = (1 + 5 ** 0.5) / 2
    import math
    n = 0
    while True:
        x = int(math.floor(n * phi))
        y = int(math.floor(n * phi * phi))
        if x > limit and y > limit:
            break
        _COLD.add((x, y))
        _COLD.add((y, x))
        n += 1


_build_cold(_COLD_LIMIT)


def _is_cold(a, b):
    return (a, b) in _COLD


def solve(text: str) -> str:
    """One line 'a b'; move single-pile i or take equal j from both."""
    a, b = (int(v) for v in text.split()[:2])
    if _is_cold(a, b):
        return 'LOSE'
    for i in range(a + 1):  # i ascending
        for j in range(b + 1):  # then j ascending -> lexicographically smallest
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # moves touch one pile, or both piles by the same amount
            if _is_cold(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'  # unreachable: a non-cold position always has a cold successor
