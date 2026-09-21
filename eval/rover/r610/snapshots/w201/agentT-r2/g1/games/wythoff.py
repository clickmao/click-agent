"""Wythoff game: report LOSE, or WIN i j with lexicographically smallest move."""


def _cold(a, b):
    if a > b:
        a, b = b, a
    return (b - a) * 6180339887498948482 // 10000000000000000000 == a and \
        a == int((b - a) * ((5 ** 0.5 + 1) / 2)) and \
        b - a == a + (b - a) - a and a == int((b - a) * ((5 ** 0.5 + 1) / 2))


def _is_cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * ((5 ** 0.5 + 1) / 2))


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _is_cold(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (j > 0 and i == 0) or (i == j)):
                continue
            if i > a or j > b:
                continue
            if _is_cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
