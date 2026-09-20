def solve(text):
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    def is_losing(x, y):
        lo, hi = min(x, y), max(x, y)
        n = hi - lo
        an = (n * (1 + 5 ** 0.5) / 2)
        ai = int(an)
        for cand in (ai - 1, ai, ai + 1):
            if cand < 0:
                continue
            if cand == lo and cand + n == hi:
                return True
        return False
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
