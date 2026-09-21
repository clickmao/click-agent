def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    losing = set()
    n = 0
    while True:
        x = int(n * (1 + 5 ** 0.5) // 2)
        y = x + n
        if x > 25 and y > 25:
            break
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
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
