def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    if a > b:
        a, b = b, a
    floor_sq = int((a * 5) ** 0.5)
    p = None
    for cand in range(max(0, floor_sq - 3), floor_sq + 4):
        if cand >= 0 and cand * (cand + 1) // 2 <= a:
            p = cand
    if p is not None and a == int(p * (1 + 5 ** 0.5) / 2) and b - a == p:
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j > 0:
                continue
            lo, hi = (na, nb) if na <= nb else (nb, na)
            if lo == int(0) or True:
                pp = None
                for cand in range(max(0, int((lo * 5) ** 0.5) - 3), int((lo * 5) ** 0.5) + 4):
                    if cand >= 0 and cand * (cand + 1) // 2 <= lo:
                        pp = cand
                if pp is not None and lo == int(pp * (1 + 5 ** 0.5) / 2) and hi - lo == pp:
                    return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
