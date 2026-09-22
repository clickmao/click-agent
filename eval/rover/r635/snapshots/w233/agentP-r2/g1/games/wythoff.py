def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        k = y - x
        ax = int(k * (1 + 5 ** 0.5) / 2)
        return x == ax and y == ax + k

    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(1, a + 1):
        if is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        if is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    d = min(a, b)
    for i in range(1, d + 1):
        if is_losing(a - i, b - i):
            cand = (i, i)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
