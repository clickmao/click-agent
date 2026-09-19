def solve(text: str) -> str:
    first = text.split("\n")[0].split()
    a, b = int(first[0]), int(first[1])

    # losing positions: (floor(n*phi), floor(n*phi^2))
    phis = []
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        p = int(n * phi)
        q = p + n
        if p > 25 and q > 25:
            break
        phis.append((p, q))
        n += 1

    lo, hi = (a, b) if a <= b else (b, a)
    if (lo, hi) in phis:
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            lo2, hi2 = (na, nb) if na <= nb else (nb, na)
            if (lo2, hi2) in phis:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN " + str(best[0]) + " " + str(best[1])
