def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[0:2])
    losing = set()
    lo, hi = min(a, b), max(a, b)
    d = 0
    while True:
        x = int(d * ((5 ** 0.5 + 1) / 2))
        y = x + d
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        d += 1
    if (lo, hi) in losing:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != j and i != 0 and j != 0:
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    i, j = best
    return "WIN %d %d" % (i, j)
