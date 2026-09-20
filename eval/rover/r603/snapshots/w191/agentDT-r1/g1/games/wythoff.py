"""Wythoff's game: losing-position check and lexicographically smallest move."""


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    phi = (1 + 5 ** 0.5) / 2
    return a == int(d * phi)


def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    if _is_losing(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if _is_losing(na, nb):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
