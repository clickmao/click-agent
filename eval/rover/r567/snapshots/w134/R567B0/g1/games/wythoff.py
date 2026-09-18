def solve(text):
    a, b = map(int, text.split())
    LIM = 64
    d = set()
    i = 0
    while True:
        t = int(i * 1.618033988749895) + i
        if t > LIM:
            break
        d.add((i, t))
        d.add((t, i))
        i += 1
    if (a, b) in d:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in d:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
