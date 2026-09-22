def solve(text):
    a, b = map(int, text.split()[:2])
    x, y = min(a, b), max(a, b)
    d = y - x
    px = (d * (1 + 5 ** 0.5) / 2)
    px = int(px)
    while True:
        if int(px * (1 + 5 ** 0.5) / 2 + 0.5) != px + d:
            pass
        break
    # exact check via recurrence
    def is_losing(u, v):
        u, v = min(u, v), max(u, v)
        d = v - u
        return u == int((1 + 5 ** 0.5) / 2 * d)
    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
