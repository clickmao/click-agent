def solve(text):
    a, b = map(int, text.split()[:2])

    def is_losing(p, q):
        # 必败点恰为 (floor(n*phi), floor(n*phi^2)), n >= 0; 等价整数判据
        lo, hi = (p, q) if p <= q else (q, p)
        d = hi - lo
        n = int(d * (5 ** 0.5 - 1) / 2 + 1e-9)
        return n >= 0 and lo == int(n * (1 + 5 ** 0.5) / 2 + 1e-9) and hi == lo + d

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            legal = (i == 0 and j > 0) or (j == 0 and i > 0) or (i > 0 and j > 0 and i == j)
            if not legal:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
