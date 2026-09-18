def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    # P-positions: (floor(n*phi), floor(n*phi*phi)) up to 40
    phi = (1 + 5 ** 0.5) / 2
    lose = set()
    for n in range(0, 60):
        x = int(n * phi)
        y = int(n * phi * phi)
        if x > 40 and y > 40:
            break
        lose.add((x, y))
        lose.add((y, x))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in lose:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
