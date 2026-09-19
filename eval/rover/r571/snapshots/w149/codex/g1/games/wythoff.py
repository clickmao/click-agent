"""Wythoff game: cold-position test and lexicographically smallest win."""


def solve(text: str) -> str:
    a, b = (int(t) for t in text.split())
    lo, hi = (a, b) if a <= b else (b, a)

    d = hi - lo
    cold = (d * (1 + 5 ** 0.5) / 2.0)
    if int(cold + 0.5) == lo:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                x, y = a - i, b - j
                if is_cold(x, y):
                    if best is None or (i, j) < best:
                        best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best


def is_cold(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    return int(d * (1 + 5 ** 0.5) / 2.0 + 0.5) == a
