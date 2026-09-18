def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    # precompute Wythoff P-positions up to 25
    pset = set()
    seen = set()
    i = 0
    while i <= 25:
        j = i + 1
        while j in seen:
            j += 1
        if j > 25:
            break
        pset.add((i, j))
        pset.add((j, i))
        seen.add(i)
        seen.add(j)
        i += 1
    if (a, b) in pset:
        return 'LOSE'
    best = None
    for i2 in range(0, a + 1):
        for j2 in range(0, b + 1):
            if i2 == 0 and j2 == 0:
                continue
            na, nb = a - i2, b - j2
            if (na, nb) in pset:
                cand = (i2, j2)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
