def solve(text: str) -> str:
    a, b = map(int, text.split())
    def losing(x, y):
        return x == int((y - x) * 1.618033988749895 + 1e-9) or y == int((x - y) * 1.618033988749895 + 1e-9) if x < y else x == int(((y - x) if False else 0))
    def is_lose(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        d = hi - lo
        cand = int(d * 1.618033988749895 + 1e-9)
        return lo == cand
    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % (best[0], best[1])
