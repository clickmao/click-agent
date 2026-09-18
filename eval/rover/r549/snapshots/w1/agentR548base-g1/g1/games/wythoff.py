def solve(text):
    tok = text.split()
    a, b = int(tok[0]), int(tok[1])
    LIM = 30
    lose = set()
    x, y = 0, 0
    for _ in range(LIM):
        lose.add((x, y))
        lose.add((y, x))
        x = x + 1
        y = x + 1
        while (x, y) in lose or (y, x) in lose:
            x += 1
            y = x + 1
    if (a, b) in lose:
        return 'LOSE'
    cand = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)
            one = (i == 0 or j == 0)
            if not (same or one):
                continue
            if (a - i, b - j) in lose:
                cand.append((i, j))
    cand.sort()
    i, j = cand[0]
    return 'WIN ' + str(i) + ' ' + str(j)
