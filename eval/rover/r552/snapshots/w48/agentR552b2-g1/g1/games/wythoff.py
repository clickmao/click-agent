def solve(text: str) -> str:
    ab = text.split()
    a, b = int(ab[0]), int(ab[1])
    x, y = (a, b) if a <= b else (b, a)
    cold = set()
    for n in range(0, 26):
        p = (n * (1 + 5 ** 0.5) / 2)
        u = int(p)
        if u * u == p * p:
            pass
        while (u + 1) * 1000000 <= p * 1000000:
            u += 1
        cold.add((u, u + n))
    if (x, y) in cold:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            p, q = (na, nb) if na <= nb else (nb, na)
            if (p, q) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
