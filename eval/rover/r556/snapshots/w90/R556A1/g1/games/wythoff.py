"""Wythoff's game: lexicographically smallest winning move (i, j)."""


def _losing(x, y):
    if x > y:
        x, y = y, x
    return x == int((y - x) * ((5 ** 0.5 + 1) / 2))


def _cands(a, b):
    out = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0:
                if i != j:
                    continue
            out.append((i, j))
    return out


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    for i, j in sorted(_cands(a, b)):
        if _losing(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
