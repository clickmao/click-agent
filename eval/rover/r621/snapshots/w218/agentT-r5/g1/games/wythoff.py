"""Wythoff game."""


def _losing(a: int, b: int) -> bool:
    x, y = min(a, b), max(a, b)
    n = y - x
    return x == (n * (1 + 5 ** 0.5) / 2) // 1


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if _losing(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    i, j = best
    return 'WIN %d %d' % (i, j)
