def solve(text):
    lines = [l for l in text.splitlines() if l.strip() != '']
    a, b = map(int, lines[0].split())

    def losing(u, v):
        x, y = min(u, v), max(u, v)
        d = y - x
        return x == ((d * (1 + 5 ** 0.5)) // 2) and y == x + d

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if i > a or j > b:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if losing(a, b):
        return 'LOSE'
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
