def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    # losing positions: (floor(phi*n), floor(phi*phi*n)) pairs, sorted
    losing = set()
    n = 0
    while True:
        p = (5 ** 0.5 + 1) / 2
        x = int(p * n)
        y = int(p * p * n)
        if x > 25 and y > 25:
            break
        if x <= 25 and y <= 25:
            losing.add((x, y))
            losing.add((y, x))
        n += 1

    if (a, b) in losing:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                best = (i, j)
                break
        if best:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
