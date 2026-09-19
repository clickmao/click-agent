def solve(text):
    a, b = map(int, text.split()[0:2])
    losing = set()
    pairs = []
    for n in range(0, 13):
        x = (n * (1 + 5 ** 0.5)) // 2
        x = int(x)
        y = x + n
        if x <= 25 and y <= 25:
            losing.add((x, y))
            losing.add((y, x))
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            ra, rb = a - i, b - j
            key = (min(ra, rb), max(ra, rb))
            if key in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
