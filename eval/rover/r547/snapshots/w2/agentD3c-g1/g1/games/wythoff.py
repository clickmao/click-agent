def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    losing = set()
    i = 0
    while True:
        x = (i * (1 + 5 ** 0.5) / 2)
        xi = int(x + 1e-9)
        yi = xi + i
        if xi > 25 and yi > 25:
            break
        losing.add((xi, yi))
        losing.add((yi, xi))
        i += 1
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i2 in range(a + 1):
        for j2 in range(b + 1):
            if i2 == 0 and j2 == 0:
                continue
            if (i2 > 0 and j2 == 0) or (i2 == 0 and j2 > 0) or (i2 == j2):
                na, nb = a - i2, b - j2
                if na < 0 or nb < 0:
                    continue
                if (na, nb) in losing:
                    cand = (i2, j2)
                    if best is None or cand < best:
                        best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
