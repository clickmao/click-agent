def solve(text: str) -> str:
    a, b = map(int, text.split())

    def is_losing(x, y):
        if x > y:
            x, y = y, x
        t = y - x
        return x == int(t * (1 + 5 ** 0.5) / 2)

    if is_losing(a, b):
        return "LOSE"

    M = 30
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
