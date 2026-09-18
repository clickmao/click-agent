def solve(text):
    a, b = map(int, text.split()[:2])
    fail = set()
    for x in range(0, 26):
        for y in range(0, 26):
            if (x, y) in fail:
                continue
            bad = False
            for i in range(x):
                if (i, y) in fail:
                    bad = True
                    break
            if not bad:
                for j in range(y):
                    if (x, j) in fail:
                        bad = True
                        break
            if not bad:
                d = min(x, y)
                for t in range(1, d + 1):
                    if (x - t, y - t) in fail:
                        bad = True
                        break
            if not bad:
                fail.add((x, y))
    if (a, b) in fail:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in fail:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
