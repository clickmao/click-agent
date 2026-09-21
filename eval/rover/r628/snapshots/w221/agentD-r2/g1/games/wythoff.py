def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    if a > b:
        a, b = b, a
    for t in range(0, min(a, b) + 1):
        if a - t == 0 and b - t == 0:
            return 'LOSE'
        x, y = a - t, b - t
        p = x * (5 ** 0.5 + 1) // 2
        if x == int(p) and y == x + int(p):
            return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            x, y = a - i, b - j
            if x < 0 or y < 0:
                continue
            lo, hi = (x, y) if x <= y else (y, x)
            lose = False
            if lo == 0 and hi == 0:
                lose = True
            else:
                p = lo * (5 ** 0.5 + 1) // 2
                if lo == int(p) and hi == lo + int(p):
                    lose = True
            if lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
