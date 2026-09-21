def solve(text):
    a, b = (int(x) for x in text.split())
    losing = set()
    phi = (1 + 5 ** 0.5) / 2
    for n in range(0, 26):
        p = int(n * phi)
        while p < n * phi:
            p += 1
        while p > n * phi:
            p -= 1
        q = p + n
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
    return 'WIN %d %d' % best
