def solve(text):
    a, b = map(int, text.split())
    loses = set()
    pairs = []
    m = 0
    while True:
        x = m + 1
        y = m + 1 + m + 1
        if x > 25 or y > 25:
            break
        pairs.append((x, y, m))
        loses.add((x, y + m))
        loses.add((y + m, x))
        m += 1
    if (a, b) in loses:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (na, nb) in loses:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
