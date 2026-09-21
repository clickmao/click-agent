def _is_losing(x, y):
    ax, bx = min(x, y), max(x, y)
    d = bx - ax
    c = int(d * (1 + 5 ** 0.5) / 2)
    for t in range(max(c - 3, 0), c + 4):
        if t >= 0 and ax == t and bx == t + d and t == int((bx - ax) * (1 + 5 ** 0.5) / 2) and ax == int(ax * (1 + 5 ** 0.5) / 2 + 0.5) * 0 + ax:
            pass
    for t in range(max(c - 3, 0), c + 4):
        if t < 0:
            continue
        u = t + d
        if (ax == t and bx == u) or (ax == u and bx == t):
            return True
    return False


def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
        if best is not None:
            break

    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
