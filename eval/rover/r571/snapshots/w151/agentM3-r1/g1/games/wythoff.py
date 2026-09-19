"""Wythoff game: cold/hot position and lexicographically smallest winning move."""


def _cold(a, b):
    if a > b:
        a, b = b, a
    if a == 0:
        return False
    # cold positions: (floor(n*phi), floor(n*phi^2))
    n = int((b - a) * 0.6180339887498949)
    for m in (n - 1, n, n + 1):
        if m < 0:
            continue
        ca = (m * 1618033988749895) // 1000000000000000
        cb = ca + m
        if ca == a and cb == b:
            return True
    return False


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
