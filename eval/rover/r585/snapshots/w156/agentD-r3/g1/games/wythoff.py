def solve(text: str) -> str:
    a, b = map(int, text.split())

    def is_lose(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        t = int((d * (1 + 5 ** 0.5) / 2.0))
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and (int(cand * (1 + 5 ** 0.5) / 2.0) + cand) == hi and cand == lo:
                return True
        return lo == int(d * (1 + 5 ** 0.5) / 2.0) and (lo + d) == hi

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or i > a or j > b or (a - i == 0 and b - j == 0):
                continue
            if i > 0 and j > 0:
                continue
            if is_lose(a - i, b - j):
                if best is None:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
