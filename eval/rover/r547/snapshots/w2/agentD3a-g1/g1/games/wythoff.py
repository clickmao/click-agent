import math


def _cold(n):
    phi = (1 + math.sqrt(5)) / 2
    return int(math.floor(n * phi))


def _is_win(a, b):
    a, b = min(a, b), max(a, b)
    n = b - a
    return a != _cold(n)


def _best_move(a, b):
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            same = (i == j)
            single = (i == 0 or j == 0)
            if not (same and i > 0) and not single:
                continue
            if not _is_win(na, nb):
                return i, j
    return None


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if not _is_win(a, b):
        return 'LOSE'
    i, j = _best_move(a, b)
    return 'WIN ' + str(i) + ' ' + str(j)
