def solve(text):
    a, b = map(int, text.split())
    pairs = set()
    for n in range(0, 26):
        t = int(n * (1 + 5 ** 0.5) / 2)
        if t > 25:
            break
        pairs.add((n, t))
        pairs.add((t, n))
    if (a, b) in pairs:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in pairs:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
