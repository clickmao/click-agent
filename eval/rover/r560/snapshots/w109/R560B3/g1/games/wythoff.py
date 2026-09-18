def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        return lo == int(d * (1 + 5 ** 0.5) / 2 + 1e-9)

    if losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = losing(a - i, b)
            elif j > 0 and i == 0:
                ok = losing(a, b - j)
            elif i == j:
                ok = losing(a - i, b - j)
            if ok:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
