def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * 1.618033988749895) and y == int(d * 2.618033988749895)

    best = None
    for i in range(a + 1):
        for j in range(a + b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if ni < 0 or nj < 0:
                continue
            removed = (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)
            if not removed:
                continue
            if losing(ni, nj):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
