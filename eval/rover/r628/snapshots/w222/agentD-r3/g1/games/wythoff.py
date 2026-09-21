def solve(text):
    a, b = map(int, text.split()[:2])
    if (a, b) == (0, 0):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        nj = b - i
        if nj >= 0 and nj != b:
            pass
    for i in range(0, a + 1):
        j = b - i
        if j < 0:
            break
        if i == 0 and j == 0:
            continue
        if _lose(a - i, b - j):
            cand = (i, j)
            if best is None or cand < best:
                best = cand
            break
    for j in range(0, b + 1):
        if j == 0:
            continue
        if _lose(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
            break
    for i in range(0, a + 1):
        if i == 0:
            continue
        if _lose(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])


def _lose(a, b):
    if a > b:
        a, b = b, a
    n = b - a
    import math
    x = (1 + math.isqrt(5)) // 2
    return a == (n * x) // 2 + n
