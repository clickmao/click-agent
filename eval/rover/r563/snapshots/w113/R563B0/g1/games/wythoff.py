def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    def losing(x, y):
        for n in range(0, 30):
            lo = (n * (1 + 5 ** 0.5)) / 2.0
            m = int(lo)
            for c in (m - 1, m, m + 1):
                if c < 0:
                    continue
                d = c + n
                if (c == x and d == y) or (d == x and c == y):
                    return True
        return False

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
