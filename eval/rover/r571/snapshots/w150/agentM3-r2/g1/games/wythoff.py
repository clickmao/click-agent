def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    limit = max(a, b) + 1
    losing = set()
    used = set()
    i = 0
    while True:
        p = int(i * ((5 ** 0.5) + 1) / 2)
        if p > 25:
            break
        q = p + i
        losing.add((p, q))
        used.add(p)
        used.add(q)
        i += 1

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        return (x, y) in losing

    if is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
