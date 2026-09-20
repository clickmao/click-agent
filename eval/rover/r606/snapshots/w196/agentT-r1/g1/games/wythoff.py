def solve(text):
    a, b = map(int, text.split())
    lo, hi = min(a, b), max(a, b)

    def is_lose(x, y):
        if x == 0 and y == 0:
            return True
        for n in range(1, 40):
            m = int(n * (1 + 5 ** 0.5) / 2 + 1e-12)
            if m == x and m + n == y:
                return True
        return False

    if is_lose(lo, hi):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            x, y = min(na, nb), max(na, nb)
            if is_lose(x, y):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % (best[0], best[1])
