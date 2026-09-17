"""Wythoff's game: remove from one pile, or equal amounts from both.

Input text format:
    one line: a b  (1..25)

solve(text) -> 'LOSE' if (a,b) is a cold position,
             else 'WIN i j' with the lexicographically smallest winning move
             (i from pile 1, j from pile 2; not both zero).
"""

from math import isqrt


def _floor_dphi(d):
    """Exact floor(d * phi), phi = (1 + sqrt(5)) / 2.

    floor(d*phi) = (d + floor(d*sqrt(5))) / 2, and
    floor(d*sqrt(5)) = isqrt(5*d*d) since 5*d*d = (d*sqrt5)^2 exactly.
    """
    return (d + isqrt(5 * d * d)) // 2


def _cold(a, b):
    """Cold position test: x == floor(d*phi) with x=min(a,b), d=|a-b|."""
    x = a if a < b else b
    d = abs(a - b)
    return x == _floor_dphi(d)


def solve(text: str) -> str:
    toks = text.split()
    a, b = int(toks[0]), int(toks[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
