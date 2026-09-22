def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    maxn = max(a, b)
    cold = set()
    i = 0
    while True:
        x = (i * (1 + 5 ** 0.5)) // 2
        x = int(x)
        y = x + i
        if x > maxn and y > maxn:
            break
        cold.add((x, y))
        i += 1
    if (a, b) in cold:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j != 0:
                continue
            elif j > 0 and i != 0:
                continue
            na, nb = a - i, b - j
            if (na, nb) in cold:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
