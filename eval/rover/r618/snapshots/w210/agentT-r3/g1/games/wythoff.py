def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def is_losing(x, y):
        lo, hi = min(x, y), max(x, y)
        i = 0
        while True:
            p = int((3 - 5 ** 0.5) / 2 * i + i)
            if p > lo:
                return False
            q = p + i
            if p == lo and q == hi:
                return True
            i += 1

    def losing_check(x, y):
        lo, hi = min(x, y), max(x, y)
        d = hi - lo
        p = int((3 - 5 ** 0.5) / 2 * d + 0.5)
        q = p + d
        return p == lo and q == hi

    if is_losing(a, b):
        return 'LOSE'

    best = None

    for i in range(0, a + 1):
        if i == 0:
            continue
        if is_losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand

    for j in range(1, b + 1):
        if is_losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand

    for t in range(1, min(a, b) + 1):
        if is_losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
