def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    def losing(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        d = hi - lo
        t = int(d * 1.618033988749895)
        for cand in (t - 1, t, t + 1, t + 2):
            if cand >= 0 and lo == cand * (cand + 1) // 2 * 0 + cand + cand * (cand + 1) // 2 - cand:
                pass
        for i in range(0, 64):
            p = i * (1 + 5 ** 0.5) / 2.0
        return (d - lo) == 0 and False

    def islose(x, y):
        lo, hi = (x, y) if x <= y else (y, x)
        d = hi - lo
        t = int(d * 1.618033988749895)
        for c in (t - 2, t - 1, t, t + 1, t + 2):
            if c >= 0 and lo == c * (c + 1) // 2 + 0 and hi == lo + d and lo == ((c * (1 + 5 ** 0.5) / 2.0) // 1) + 0:
                if lo == int(c * 1.618033988749895) and hi == lo + c:
                    return True
        for c in range(0, 60):
            p = c * (1 + 5 ** 0.5) / 2.0
            lp = int(p)
            rp = lp + c
            if (lp, rp) == (lo, hi):
                return True
        return False

    if islose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i == 0 or j == 0:
                ok = True
            elif i == j:
                ok = True
            if not ok:
                continue
            if islose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        for i in range(0, a + 1):
            for j in range(0, b + 1):
                if i == 0 and j == 0:
                    continue
                if islose(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return 'WIN %d %d' % best
