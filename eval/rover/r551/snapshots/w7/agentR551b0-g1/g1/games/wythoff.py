def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    losing = set()
    for i in range(1, 26):
        for j in range(i, 26):
            ok = True
            if (i, j) in losing:
                ok = False
            if ok:
                for x, y in list(losing):
                    if x == i or y == j or (i - x) == (j - y):
                        ok = False
                        break
            if ok:
                losing.add((i, j))
    def is_lose(x, y):
        if x > y:
            x, y = y, x
        return (x, y) in losing
    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
