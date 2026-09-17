"""Wythoff's game: detection of losing positions and lexicographically
smallest winning move (i, j) = (removed from pile 1, removed from pile 2)."""

import math


def solve(text: str) -> str:
    for line in text.split("\n"):
        if line.strip():
            a, b = (int(x) for x in line.split())
            break

    def is_losing(x: int, y: int) -> bool:
        # Wythoff losing pairs: (floor(n*phi), floor(n*phi^2)), n >= 0.
        if x > y:
            x, y = y, x
        n = y - x
        phi = (1 + math.sqrt(5)) / 2
        return x == int(math.floor(n * phi))

    if is_losing(a, b):
        return "LOSE"

    # Enumerate every legal move; pick lexicographically smallest (i, j).
    best = None
    # Move type (i): take from one pile only.
    for i in range(0, a + 1):
        if i > 0 and is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if j > 0 and is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # Move type (ii): take the same amount from both piles.
    for t in range(1, min(a, b) + 1):
        if is_losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return "WIN %d %d" % best
