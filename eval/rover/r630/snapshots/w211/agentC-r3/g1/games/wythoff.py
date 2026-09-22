def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == int(((y - x) * (1 + 5 ** 0.5) / 2))

    if losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i > a or j > b:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
