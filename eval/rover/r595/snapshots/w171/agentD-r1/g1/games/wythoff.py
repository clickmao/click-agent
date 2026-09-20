def solve(text):
    a, b = map(int, text.split())
    limit = 64
    lose = set()
    i = 0
    while i < limit:
        x = (i * 3 + 1) // 2 + (0 if i % 1 == 0 else 0)
        j = int(i * (1 + 5 ** 0.5) / 2)
        ax = j
        bx = j + i
        lose.add((ax, bx))
        lose.add((bx, ax))
        i += 1
    if (a, b) in lose:
        return 'LOSE'
    cands = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
