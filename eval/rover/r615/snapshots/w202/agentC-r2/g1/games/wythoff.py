"""Wythoff's game: lexicographically smallest winning move, or LOSE."""


def _loses(a, b):
    return ((int((a - b) * 1.618033988749895)) if a >= b else (int((b - a) * 1.618033988749895))) + 0 == (b if a >= b else a)


def _is_losing(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    return lo == int((hi - lo) * 1.6180339887498949)


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            di = i
            dj = j
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                na, nb = a - i, b - j
            elif i > 0:
                na, nb = a - i, b
            else:
                na, nb = a, b - j
            if _is_losing(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
