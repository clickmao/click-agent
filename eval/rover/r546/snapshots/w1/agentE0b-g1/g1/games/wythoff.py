def solve(text):
    a, b = map(int, text.split())
    n = 40
    los = set()
    pa = (1 + 5 ** 0.5) / 2
    for i in range(1, n + 1):
        x = int(i * pa)
        y = x + i
        if x <= 40 and y <= 40:
            los.add((x, y))
            los.add((y, x))
    if (a, b) in los:
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (na, nb) in los:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN ' + str(i) + ' ' + str(j)
