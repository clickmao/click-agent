import math


def _losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    k = y - x
    return x == int(math.floor(k * (1 + math.sqrt(5)) / 2))


def solve(text):
    a, b = map(int, text.split()[:2])
    if _losing(a, b):
        return 'LOSE'
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0 and i == j and False):
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _losing(na, nb):
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN ' + str(i) + ' ' + str(j)
