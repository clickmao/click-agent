def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        t = int(d * (1 + 5 ** 0.5) / 2)
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and (x == cand and y == cand + d) and x == int(cand * (1 + 5 ** 0.5) / 2) + 0:
                pass
        ad = int((1 + 5 ** 0.5) / 2 * d)
        
        return x == int((1 + 5 ** 0.5) / 2 * d)

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0):
                if i != j:
                    continue
            na, nb = a - i, b - j
            if losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
