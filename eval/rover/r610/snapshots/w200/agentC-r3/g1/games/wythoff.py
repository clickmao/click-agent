"""Wythoff game: lexicographically smallest winning move (i, j).

Losing positions are the Beatty pairs (floor(n*phi), floor(n*phi^2)) with
phi = (1 + sqrt(5)) / 2.  The losing-position predicate is precomputed by a
plain DP over the 0..25 range, so no golden-ratio rounding is involved.
"""

LIMIT = 32

# losing[b][a] with a <= b, table sized generously above the 1..25 input range
_LOSING = [[False] * (LIMIT + 1) for _ in range(LIMIT + 1)]
for _b in range(LIMIT + 1):
    for _a in range(_b + 1):
        _lose = False
        for _i in range(_b + 1):
            _j0 = 0 if _i == 0 else _i
            for _j in range(_j0, _b + 1):
                if _i == 0 and _j == 0:
                    continue
                if _i > _a or _j > _b:
                    continue
                if not (_i == 0 or _j == 0 or _i == _j):
                    continue
                if _i <= _a and _j <= _b and _LOSING[_b - _j][_a - _i]:
                    _lose = True
                    break
            if _lose:
                break
        _LOSING[_b][_a] = not _lose


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    return _LOSING[b][a]


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
