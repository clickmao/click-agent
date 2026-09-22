def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    losing = set()
    for i in range(26):
        for j in range(26):
            ok = True
            for (x, y) in losing:
                if x == i or y == j or (i - x) == (j - y):
                    ok = False
                    break
            if ok:
                losing.add((i, j))
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
