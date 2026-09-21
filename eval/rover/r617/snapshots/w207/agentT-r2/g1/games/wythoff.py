def solve(text):
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])
    losing = set()
    for x in range(0, a + 1):
        for y in range(0, b + 1):
            best = None
            for i in range(0, x + 1):
                if (i, 0) != (0, 0) and (x - i, y) in losing:
                    best = (i, 0)
                    break
            if best is None:
                for j in range(0, y + 1):
                    if (j != 0) and (x, y - j) in losing:
                        best = (0, j)
                        break
            if best is None:
                r = min(x, y)
                for t in range(1, r + 1):
                    if (x - t, y - t) in losing:
                        best = (t, t)
                        break
            if best is None:
                losing.add((x, y))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        if (i, 0) != (0, 0) and (a - i, b) in losing:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    for j in range(0, b + 1):
        if (j != 0) and (a, b - j) in losing:
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    r = min(a, b)
    for t in range(1, r + 1):
        if (a - t, b - t) in losing:
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return 'WIN %d %d' % best
