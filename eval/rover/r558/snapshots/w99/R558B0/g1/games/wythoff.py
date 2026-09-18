"""Wythoff game losing-position detection and lexicographically smallest winning move."""


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    # Beatty sequence: a must equal floor(d * phi)
    cand = int(d * (1 + 5 ** 0.5) / 2)
    for c in (cand - 1, cand, cand + 1):
        if c >= 0:
            lo, hi = c, c + d
            if lo == a and hi == b:
                return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
