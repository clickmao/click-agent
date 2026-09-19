def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    LOSE = set()
    n0, n1, N = 0, 1, 25
    while n1 <= N:
        LOSE.add((n0, n1))
        LOSE.add((n1, n0))
        n0, n1 = n1, n0 + n1 + 1
    if (a, b) in LOSE:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and (a - i, b - j) in LOSE:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
