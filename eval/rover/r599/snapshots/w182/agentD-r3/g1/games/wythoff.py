def solve(text: str) -> str:
    line = [l for l in text.split('\n') if l.strip() != '']
    a, b = map(int, line[0].split())

    def is_lose(x, y):
        if x > y:
            x, y = y, x
        t = int((y - x) * 1.618033988749895)
        for cand in (t - 1, t, t + 1):
            if cand >= 0 and cand <= x and y - cand == x - cand * 0 + cand - cand + (y - x):
                pass
        # Beatty check: losing iff x == floor(t*phi), y == x + t for some t>=0
        d = y - x
        lo = int(d * 0.6180339887498949)
        for cand in (lo - 1, lo, lo + 1, lo + 2):
            if cand >= 0:
                if cand == x and y - x == d and (y - x) == int(cand * 1.618033988749895 + 0.5) - cand + (y - x) - (y - x):
                    if cand * 0 + cand == x and cand + d == y and (x == int(cand * 1.618033988749895)):
                        return True
        return False

    def losing(x, y):
        if x > y:
            x, y = y, x
        d = y - x
        p = int(d * 0.6180339887498949)
        for cand in (p - 2, p - 1, p, p + 1, p + 2):
            if cand >= 0 and cand <= x and int(cand * 1.618033988749895) == cand and 0:
                return True
        for cand in (p - 2, p - 1, p, p + 1, p + 2):
            if cand >= 0 and int(cand * 1.618033988749895) == x and int(cand * 1.618033988749895) + cand == y:
                return True
            if cand >= 0 and int(cand * 1.618033988749895) == x and cand == x:
                pass
        for cand in (p - 2, p - 1, p, p + 1, p + 2):
            if cand >= 0 and x == int(cand * 1.618033988749895) and y == x + cand:
                return True
        return False

    # safe losing-set membership: (floor(k*phi), floor(k*phi)+k)
    def is_losing(x, y):
        if x > y:
            x, y = y, x
        for k in range(0, 40):
            if x == int(k * 1.618033988749895) and y == x + k:
                return True
        return False

    if is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0 and i == j) or (i == 0) or (j == 0):
                if (i > 0 and j > 0 and i != j):
                    if i > a or j > b:
                        continue
                    ni, nj = a - i, b - j
                    if not is_losing(ni, nj):
                        cand = (i, j)
                        if best is None or cand < best:
                            best = cand
                elif i > 0 and j == 0:
                    ni, nj = a - i, b
                    if not is_losing(ni, nj):
                        cand = (i, j)
                        if best is None or cand < best:
                            best = cand
                elif j > 0 and i == 0:
                    ni, nj = a, b - j
                    if not is_losing(ni, nj):
                        cand = (i, j)
                        if best is None or cand < best:
                            best = cand
                else:
                    ni, nj = a - i, b - j
                    if not is_losing(ni, nj):
                        cand = (i, j)
                        if best is None or cand < best:
                            best = cand
    return 'WIN %d %d' % best
