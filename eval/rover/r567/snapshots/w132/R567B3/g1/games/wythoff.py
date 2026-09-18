def solve(text: str) -> str:
    a, b = map(int, text.split())
    def lose(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        return x == int(d * (1 + 5 ** 0.5) / 2)
    if lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i == 0 and j == 0):
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if lose(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
