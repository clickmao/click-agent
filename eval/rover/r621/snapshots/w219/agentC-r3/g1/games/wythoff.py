def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    lose = []
    m = 0
    while True:
        x = (m * (1 + 5 ** 0.5)) / 2.0
        xi = int(x + 0.5)
        if xi > 25:
            break
        yi = xi + m
        if yi > 25:
            break
        lose.append((xi, yi))
        lose.append((yi, xi))
        m += 1
    lose_set = set(lose)
    if (a, b) in lose_set:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)
            one_pile = (i == 0) or (j == 0)
            if not (same or one_pile):
                continue
            if (a - i, b - j) in lose_set:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
