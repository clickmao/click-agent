def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    # cold positions (P-positions) for Wythoff's game: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    for n in range(0, 30):
        p = int(n * phi)
        q = int(n * phi * phi)
        cold.add((p, q))
        cold.add((q, p))

    if (a, b) in cold:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in cold:
                best = (i, j)
                break
        if best is not None:
            break

    return "WIN " + str(best[0]) + " " + str(best[1])
