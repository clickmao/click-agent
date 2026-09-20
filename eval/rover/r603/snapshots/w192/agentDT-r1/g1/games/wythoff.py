def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    phi = (1 + 5 ** 0.5) / 2
    limit = 60
    cold = set()
    for n in range(0, limit):
        x = int(n * phi)
        cold.add((x, x + n))
        cold.add((x + n, x))

    if (a, b) in cold:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in cold:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
