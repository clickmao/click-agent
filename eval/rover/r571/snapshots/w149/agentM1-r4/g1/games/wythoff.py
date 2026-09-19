"""Wythoff's game: LOSE for a cold position, else WIN i j (lexicographically smallest move).

A position (a, b) with a <= b is cold iff a == floor(phi * (b - a)) where phi = (1 + sqrt 5) / 2.
"""

from math import isqrt


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    cand = (isqrt(5 * d * d) + d) // 2
    return a == cand


def solve(text):
    a, b = map(int, text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_cold(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
