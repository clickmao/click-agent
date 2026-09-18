def solve(text):
    a, b = map(int, text.split())
    if a > b:
        a, b = b, a
    d = b - a
    ax = (1 + 5 ** 0.5) / 2
    p = int((d * ax) + 1e-9)
    if p == a:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            ni, nj = a - i, b - j
            x, y = (ni, nj) if ni <= nj else (nj, ni)
            dd = y - x
            pp = int((dd * ax) + 1e-9)
            if pp == x:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
