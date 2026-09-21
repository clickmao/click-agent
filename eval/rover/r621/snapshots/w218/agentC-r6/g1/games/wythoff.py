"""Wythoff's game: print the lexicographically smallest winning move."""

import math

LIMIT = 100
COLD = set()


def _build():
    if COLD:
        return
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    for k in range(1, LIMIT + 1):
        a = int(math.floor(k * phi))
        b = a + k
        COLD.add((a, b))
        COLD.add((b, a))


def _is_cold(a, b) -> bool:
    _build()
    return (a, b) in COLD


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(t) for t in lines[idx].split()[:2])

    if _is_cold(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        if i == 0:
            continue
        if _is_cold(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if _is_cold(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    for t in range(1, min(a, b) + 1):
        if _is_cold(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
