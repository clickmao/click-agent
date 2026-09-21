def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    phi = (1 + 5 ** 0.5) / 2

    def losing(x, y):
        if x > y:
            x, y = y, x
        n = y - x
        return x == int(n * phi)

    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if losing(a - i, b - j):
                cands.append((i, j))
    if not cands:
        return 'LOSE'
    cands.sort()
    i, j = cands[0]
    return 'WIN ' + str(i) + ' ' + str(j)
