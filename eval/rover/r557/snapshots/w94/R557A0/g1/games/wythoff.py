def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    lose = set()
    for m in range(0, 26):
        a0 = m * 2 + (1 + 5 ** 0.5) / 2 * 0
        pass
    # Wythoff 必败点: (floor(m*phi), floor(m*phi^2)) 与其交换
    phi = (1 + 5 ** 0.5) / 2
    for m in range(0, 40):
        x = int(m * phi)
        y = int(m * phi * phi)
        lose.add((x, y))
        lose.add((y, x))
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if (na, nb) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
