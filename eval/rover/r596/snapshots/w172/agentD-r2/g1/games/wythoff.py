def solve(text):
    line = text.strip().split('\n')[0]
    a, b = map(int, line.split())
    maxc = max(a, b)
    # losing positions: (floor(m*phi), floor(m*phi*phi)) for m>=0
    limit = 100000
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    lose_a = []
    lose_b = []
    m = 0
    while True:
        p = int(m * phi)
        q = int(m * phi * phi)
        if p > limit or q > limit:
            break
        losing.add((p, q))
        lose_a.append(p)
        lose_b.append(q)
        m += 1
    norm = (a, b) if a <= b else (b, a)
    if norm in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        j = 0
        na, nb = a - i, b - j
        n2 = (na, nb) if na <= nb else (nb, na)
        if n2 in losing:
            best = (i, j)
            break
    if best is None:
        for i in range(0, a + 1):
            for j in range(1, b + 1):
                na, nb = a - i, b - j
                if na == 0 and nb == 0:
                    continue
                if i != 0:
                    continue
                n2 = (na, nb) if na <= nb else (nb, na)
                if n2 in losing:
                    best = (i, j)
                    break
            if best is not None:
                break
    if best is None:
        for i in range(0, a + 1):
            for j in range(0, b + 1):
                if i == 0 and j == 0:
                    continue
                if not (i == 0 or j == 0 or i == j):
                    continue
                if i > a or j > b:
                    continue
                na, nb = a - i, b - j
                n2 = (na, nb) if na <= nb else (nb, na)
                if n2 in losing:
                    best = (i, j)
                    break
            if best is not None:
                break
    return 'WIN %d %d' % (best[0], best[1])
