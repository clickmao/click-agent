def solve(text):
    lines = text.splitlines()
    if not lines:
        return ""
    a, b = map(int, lines[0].split())
    losing = set()
    for x in range(0, 26):
        for y in range(x, 26):
            ok = True
            for (u, v) in losing:
                if u == x or v == y or (v - u) == (y - x):
                    ok = False
                    break
            if ok:
                losing.add((x, y))
                break
    def is_losing(x, y):
        p = (min(x, y), max(x, y))
        return p in losing
    if is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0:
                if i == j and is_losing(a - i, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
                continue
            if i == 0:
                if is_losing(a, b - j):
                    if best is None or (i, j) < best:
                        best = (i, j)
            else:
                if is_losing(a - i, b):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
