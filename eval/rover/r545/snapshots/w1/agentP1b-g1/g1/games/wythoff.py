import math


def _cold(a, b):
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    cand = int(math.floor(d * (1 + math.sqrt(5)) / 2))
    return x == cand and y == x + d


def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _cold(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                na, nb = a - i, b - j
                if _cold(na, nb):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
