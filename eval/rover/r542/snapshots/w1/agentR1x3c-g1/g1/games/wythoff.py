def _parse(text):
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    a, b = map(int, lines[i].split())
    return a, b


def _losing(x, y):
    if x > y:
        x, y = y, x
    n = y - x
    tx = n * 0.6180339887498949
    import math
    ax = int(math.floor(tx))
    for cand in (ax - 1, ax, ax + 1):
        if cand >= 0:
            if x == cand and y == cand + n:
                return True
    return False


def solve(text):
    a, b = _parse(text)
    if _losing(a, b):
        return 'LOSE'
    best = None
    n = max(a, b)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
