def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    p = []
    i = 0
    occupied = set()
    while len(p) < 30:
        while i in occupied:
            i += 1
        x, y = i, i + len(p) + 1
        p.append((x, y))
        occupied.add(x)
        occupied.add(y)
    losing = set()
    for x, y in p:
        losing.add((x, y))
        losing.add((y, x))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                best = (i, j)
                break
        if best:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
