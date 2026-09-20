from math import floor, sqrt


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    i = (int(floor((b - a) * (1 + sqrt(5)) / 2 + 1e-9)))
    return a == i and b == i + (b - a)


def _losing_pairs(limit):
    pairs = []
    used = set()
    i = 0
    while True:
        a = int(floor(i * (1 + sqrt(5)) / 2 + 1e-9))
        b = a + i
        if b > limit:
            break
        pairs.append((a, b))
        used.add(a)
        used.add(b)
        i += 1
    return pairs


def solve(text):
    a, b = map(int, text.split()[0:2])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    # option (i): take from one pile only
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0) or (i == 0 and j == 0):
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    # option (ii): take same positive amount from both piles
    for t in range(1, min(a, b) + 1):
        if _is_losing(a - t, b - t):
            if best is None or (t, t) < best:
                best = (t, t)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
