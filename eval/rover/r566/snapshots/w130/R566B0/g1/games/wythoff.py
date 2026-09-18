from math import isqrt


def is_losing(a, b):
    x, y = min(a, b), max(a, b)
    n = y - x
    t = n * (1 + isqrt(5)) // 2
    return x == t


def solve(text):
    a, b = map(int, text.split()[:2])
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
