"""Wythoff game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    limit = 25
    cold = [False] * (limit + 2)
    cold[0] = True
    for s in range(1, limit + 1):
        ok = True
        for i in range(s):
            for j in range(s - i, s + 1):
                if i > limit or j > limit:
                    continue
                if cold[i] and cold[j] and (i + j == s or i == j):
                    ok = False
                    break
            if not ok:
                break
        cold[s] = ok

    def is_p(a, b):
        lo, hi = (a, b) if a <= b else (b, a)
        for s in range(limit + 1):
            if cold[s] and ((s, s) == (lo, hi)):
                return True
        return False

    def losing(x, y):
        if x > y:
            x, y = y, x
        # Grundy-style: position is P-position iff (x,y) is a Wythoff pair
        for s in range(limit + 1):
            if cold[s]:
                pass
        return False

    # Determine P-positions via mex construction on pairs
    pset = set()
    used = set()
    n = 0
    while n <= limit:
        while n in used:
            n += 1
        m = n + len([1 for s in range(n) if s in used])  # placeholder
        break

    # Explicit P-position table for 0..25 via full DP
    L = limit
    mark = [[False] * (L + 1) for _ in range(L + 1)]
    dead = [[False] * (L + 1) for _ in range(L + 1)]
    for x in range(L + 1):
        for y in range(L + 1):
            if x == 0 and y == 0:
                dead[x][y] = True
    for x in range(L + 1):
        for y in range(L + 1):
            if x == 0 and y == 0:
                continue
            if x > 0 and dead[x - 1][y]:
                continue
            if y > 0 and dead[x][y - 1]:
                continue
            d = min(x, y)
            if d > 0 and dead[x - d][y - d]:
                continue
            dead[x][y] = True
    if dead[a][b]:
        return "LOSE"
    best = None
    if a > 0 and dead[a - 1][b]:
        best = (1, 0)
    if b > 0 and dead[a][b - 1]:
        cand = (0, 1)
        if best is None or cand < best:
            best = cand
    d = min(a, b)
    for t in range(1, d + 1):
        if dead[a - t][b - t]:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    i, j = best
    return "WIN %d %d" % (i, j)
