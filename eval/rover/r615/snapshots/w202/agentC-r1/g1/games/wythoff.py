def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    maxn = max(a, b) + 1
    losing = set()
    for k in range(maxn + 2):
        n = (k * (1 + 5 ** 0.5)) // 2
        n = int(n)
        m = n + k
        if n > maxn + 1 or m > maxn + 2:
            break
        if n == m:
            continue
        losing.add((n, m))
    if (a, b) in losing or (b, a) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing or (nb, na) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
