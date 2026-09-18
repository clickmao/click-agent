"""Wythoff's game: remove from one pile or equal amounts from both piles."""

_PHI = (1 + 5 ** 0.5) / 2


def _is_lose(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    d = y - x
    if x == int(d * _PHI):
        return True
    return x == y == 0


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if _is_lose(a, b):
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
