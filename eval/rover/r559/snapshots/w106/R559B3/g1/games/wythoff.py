def solve(text):
    a, b = map(int, text.split()[0:2])
    losing = set()
    for i in range(0, 26):
        for j in range(i, 26):
            ok = True
            # check no move leads to an existing losing pair
            for t in range(1, i + 1):
                if (i - t, j) in losing or (j, i - t) in losing:
                    ok = False
                    break
            if ok:
                for t in range(1, j + 1):
                    if (i, j - t) in losing or (j - t, i) in losing:
                        ok = False
                        break
            if ok:
                for t in range(1, min(i, j) + 1):
                    if (i - t, j - t) in losing or (j - t, i - t) in losing:
                        ok = False
                        break
            if ok:
                losing.add((i, j))
                losing.add((j, i))
    if (a, b) in losing:
        return "LOSE"
    best = None
    cands = []
    for i in range(a + 1):
        cands.append((i, 0))
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            cands.append((i, j))
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na >= 0 and nb >= 0 and (na, nb) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
