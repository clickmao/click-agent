import math


LIMIT = 64


def _cold(a, b):
    if a > b:
        a, b = b, a
    for i in range(0, LIMIT + 1):
        x = int(math.floor(i * (1 + math.sqrt(5)) / 2))
        y = x + i
        if (a, b) == (x, y):
            return True
        if x > a and x > b:
            break
    return False


def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if a - i < 0 or b - j < 0:
                continue
            if _cold(a - i, b - j):
                cands.append((i, j))
    if not cands:
        return 'LOSE'
    i, j = min(cands)
    return 'WIN %d %d' % (i, j)
