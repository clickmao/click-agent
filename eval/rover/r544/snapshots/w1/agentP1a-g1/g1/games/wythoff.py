def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    cache = {}

    def lose(x, y):
        if x > y:
            x, y = y, x
        key = (x, y)
        if key in cache:
            return cache[key]
        res = False
        for i in range(1, x + 1):
            if lose(x - i, y):
                continue
            res = True
            break
        if not res:
            for j in range(1, y + 1):
                if lose(x, y - j):
                    continue
                res = True
                break
        if not res:
            for d in range(1, min(x, y) + 1):
                if lose(x - d, y - d):
                    continue
                res = True
                break
        cache[key] = res
        return res

    if not lose(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i == 0:
                ok = j <= b
            elif j == 0:
                ok = i <= a
            elif i == j:
                ok = i <= a and i <= b
            else:
                ok = False
            if not ok:
                continue
            if not lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
