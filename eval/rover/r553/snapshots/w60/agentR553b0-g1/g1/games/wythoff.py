"""Wythoff game: losing positions are (floor(phi*i), floor(phi^2*i)).

A position (a, b) is a P-position iff |a - b| = i and min(a, b) = floor(phi*i)
for some i >= 0.  For a winning position the lexicographically smallest
winning move is reported as the smallest removal pair (i, j) (i for heap 1,
j for heap 2) that lands on a P-position, compared lexicographically by (i, j).
"""

import math


def _phi():
    return (1.0 + math.sqrt(5.0)) / 2.0


def _p_positions(limit):
    phi = _phi()
    pos = set()
    i = 0
    while True:
        a = int(math.floor(phi * i))
        b = int(math.floor(phi * phi * i))
        if a > limit and b > limit:
            break
        pos.add((a, b))
        i += 1
    return pos


def _is_losing(a, b, pos):
    return (a, b) in pos or (b, a) in pos


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    limit = max(a, b)
    pos = _p_positions(limit)

    if _is_losing(a, b, pos):
        return "LOSE"

    cands = []
    # (i): remove i from heap 1 only -> (a - i, b), i >= 1, i <= a
    for i in range(1, a + 1):
        if _is_losing(a - i, b, pos):
            cands.append((i, 0))
    # (ii): remove j from heap 2 only -> (a, b - j), j >= 1, j <= b
    for j in range(1, b + 1):
        if _is_losing(a, b - j, pos):
            cands.append((0, j))
    # (iii): remove i from both -> (a - i, b - i), i >= 1
    for i in range(1, min(a, b) + 1):
        if _is_losing(a - i, b - i, pos):
            cands.append((i, i))
    # (iv): remove i from heap 1 and j from heap 2 with neither zero
    for i in range(1, a + 1):
        for j in range(1, b + 1):
            if _is_losing(a - i, b - j, pos):
                cands.append((i, j))

    cands.sort()
    i, j = cands[0]
    return "WIN %d %d" % (i, j)
