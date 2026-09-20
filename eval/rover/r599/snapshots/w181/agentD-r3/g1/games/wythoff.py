def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if b < a:
        a, b = b, a
    losing = set()
    for n in range(0, 26):
        losing.add((int(n * (1 + 5 ** 0.5) / 2) + n, int(n * (1 + 5 ** 0.5) / 2) + 2 * n))
    oa = int(tokens[0])
    ob = int(tokens[1])
    if (oa, ob) in losing or (ob, oa) in losing:
        return 'LOSE'
    best = None
    for i in range(oa + 1):
        for j in range(ob + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = oa - i, ob - j
            if (na, nb) in losing or (nb, na) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
