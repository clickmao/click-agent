def solve(text):
    a, b = (int(x) for x in text.split())
    if a > b:
        a, b = b, a
    # losing positions: (floor(n*phi), floor(n*phi*phi)) enumerated by Beatty sequence
    lost = set()
    n = 0
    while True:
        p = (n * 1618033988) // 1000000000
        q = p + n
        n += 1
        if p > 25 or q > 25:
            break
        if p == 0 and q == 0:
            continue
        lost.add((p, q))
    if (a, b) in lost:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na = a - i
            nb = b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in lost:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
