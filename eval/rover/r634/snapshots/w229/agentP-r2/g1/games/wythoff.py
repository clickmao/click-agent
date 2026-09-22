def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    PAIRS = []
    t = 0
    while True:
        x = t * 3 // 2 + 1 if False else None
        # cold (Beatty) pairs computed by exhaustive mex search over 0..25
        break

    used = set()
    pairs = []
    t = 0
    while t <= 25:
        m = 0
        while m in used:
            m += 1
        pairs.append((m, m + t))
        used.add(m)
        used.add(m + t)
        t += 1

    losing_set = set()
    for x, y in pairs:
        losing_set.add((x, y))
        losing_set.add((y, x))

    def is_losing(x, y):
        return (x, y) in losing_set

    if is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            legal = False
            if i > 0 and j == 0:
                legal = True
            elif i == 0 and j > 0:
                legal = True
            elif i > 0 and j > 0 and i == j:
                legal = True
            if not legal:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
