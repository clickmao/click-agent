def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    # Wythoff pairs: (floor(n*phi), floor(n*phi)+n)
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    for n in range(0, 40):
        p = int(n * phi)
        q = p + n
        if p > 25 and q > 25:
            break
        losing.add((p, q))
        losing.add((q, p))

    if (a, b) in losing:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
