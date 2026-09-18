"""Wythoff's game: report the lexicographically smallest winning move.

A position (x, y) is losing iff, with x <= y, x equals floor(phi * (y - x)).
"""


def _is_losing(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    return x == int((y - x) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
