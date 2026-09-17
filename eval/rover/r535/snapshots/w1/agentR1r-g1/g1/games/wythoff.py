def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    LIM = 26
    lose = set()
    for n in range(0, LIM + 1):
        x = (n * (1 + 5 ** 0.5)) // 2
        x = int(x)
        y = x + n
        if x <= LIM and y <= LIM:
            lose.add((x, y))
            lose.add((y, x))
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
