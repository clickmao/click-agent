"""Wythoff's game: a b; output 'LOSE' for cold positions else 'WIN i j' lexicographically smallest move.

A position (a, b) is a cold (previous-player-win / losing for mover) position iff
it is (floor(phi*t), floor(phi^2*t)) up to order, for some t >= 0 (Beatty sequences).
Any non-cold position has a winning move to a cold position; the lexicographically
smallest such (i, j) is reported.
"""

import math


def _phi_minus_one():
    return (math.sqrt(5.0) - 1.0) / 2.0


def _cold(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    t = int(a / _phi_minus_one())
    for cand in (t - 1, t, t + 1):
        if cand < 0:
            continue
        x = int(math.floor(cand * _phi_minus_one() + 1e-9))
        y = x + cand
        if x == a and y == b:
            return True
    return False


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if _cold(a, b):
        return "LOSE"

    best = None
    # option (i): remove from a single pile
    for i in range(0, a + 1):
        for j in (0,):
            na, nb = a - i, b - j
            if i == 0 and j == 0:
                continue
            if _cold(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    for j in range(0, b + 1):
        for i in (0,):
            na, nb = a - i, b - j
            if i == 0 and j == 0:
                continue
            if _cold(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    # option (ii): remove equal positive amount from both piles
    for d in range(1, min(a, b) + 1):
        na, nb = a - d, b - d
        if _cold(na, nb):
            cand = (d, d)
            if best is None or cand < best:
                best = cand

    return "WIN " + str(best[0]) + " " + str(best[1])
