"""Wythoff's game: losing positions are (floor(n*phi), floor(n*phi^2))."""

import math


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    n = b - a
    # losing iff a == floor(n*phi)
    phi = (1 + math.sqrt(5)) / 2
    return a == int(math.floor(n * phi))


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return 'LOSE'

    # Find lexicographically smallest (i, j) with i,j>=0, not both 0,
    # leaving a losing position: (a-i, b-j).
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if _is_losing(a - i, b - j):
                if best is None:
                    best = (i, j)
                    break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
