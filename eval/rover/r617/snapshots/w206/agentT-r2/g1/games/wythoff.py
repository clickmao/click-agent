def solve(text):
    t = text.split()
    a = int(t[0])
    b = int(t[1])
    phi = (1 + 5 ** 0.5) / 2.0

    def losing(x, y):
        if x > y:
            x, y = y, x
        n = y - x
        f = int(n * phi + 1e-9)
        return x == f and y == x + n

    if losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
