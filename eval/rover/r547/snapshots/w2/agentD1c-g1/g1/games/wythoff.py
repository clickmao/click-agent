def solve(text):
    line = text.strip().split('\n')[0]
    a, b = (int(x) for x in line.split())
    lose = set()
    for x in range(0, 26):
        for y in range(x, 26):
            ok = True
            for (u, v) in lose:
                if u == x or v == y or (v - u) == (y - x):
                    ok = False
                    break
            if ok:
                lose.add((x, y))
    x0, y0 = (a, b) if a <= b else (b, a)
    if (x0, y0) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            nb = (i == 0) or (j == 0 and i == j) or (i == j)
            if not nb:
                continue
            na, nbb = a - i, b - j
            xx, yy = (na, nbb) if na <= nbb else (nbb, na)
            if (xx, yy) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
