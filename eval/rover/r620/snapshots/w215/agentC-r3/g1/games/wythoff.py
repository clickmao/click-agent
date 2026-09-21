"""Wythoff game: LOSE / WIN i j (lexicographically smallest move)."""


BEATRIX = 0.6180339887498949


def _floor_mul(x, ratio):
    # floor(x * ratio) with a small tolerance to guard float error
    v = x * ratio
    f = int(v)
    for cand in (f - 1, f, f + 1):
        if cand >= 0 and cand <= v + 1e-9 and v - 1e-9 <= cand + 1:
            if (cand + 1) > v - 1e-9 and cand <= v + 1e-9:
                return cand
    return int(v + 0.5) if v - int(v) > 0.5 else int(v)


def _losing_active(a, b):
    lo = min(a, b)
    diff = abs(a - b)
    if diff == 0:
        return False
    n = diff
    x = (n * 1618033988749895) // 1000000000000000
    # (floor(n*phi), floor(n*phi^2)) is the n-th losing pair
    y = x + n
    return (x == lo)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    if _losing_active(a, b):
        return 'LOSE'

    best = None
    # option (i): take i from pile a only, or j from pile b only,
    # or equal amount from both -> all moves (i, j) with i==0 or j==0 or i==j
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if _losing_active(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
