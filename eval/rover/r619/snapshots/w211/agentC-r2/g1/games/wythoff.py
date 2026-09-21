"""Wythoff game: losing positions and lexicographically minimal winning move."""


def _losing(a, b):
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1.0 + 5.0 ** 0.5) / 2.0 + 1e-9)


def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    if _losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == j and i > 0:
                pass
            elif i > 0 and j > 0 and i != j:
                continue
            elif i > 0 and j > 0:
                continue
            if _losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
