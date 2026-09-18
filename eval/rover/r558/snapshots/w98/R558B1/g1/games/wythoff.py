def solve(text):
    a, b = (int(x) for x in text.split())
    # P-positions: (floor(n*phi), floor(n*phi^2))
    import math
    phi = (1 + math.sqrt(5.0)) / 2.0
    pset = set()
    for n in range(0, 40):
        u = int(math.floor(n * phi))
        v = int(math.floor(n * phi * phi))
        pset.add((u, v))
        pset.add((v, u))
    if (a, b) in pset:
        return 'LOSE'
    best = None
    # single pile: (i,0) and (0,j)
    for i in range(0, a + 1):
        if (a - i, b) in pset:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if (a, b - j) in pset:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # both piles: equal amount
    for d in range(1, min(a, b) + 1):
        if (a - d, b - d) in pset:
            cand = (d, d)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
