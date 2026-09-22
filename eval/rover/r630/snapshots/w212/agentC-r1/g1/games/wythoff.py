def solve(text: str) -> str:
    a, b = map(int, text.split())
    pairs = set()
    for n in range(0, 60):
        x = (n * (1 + 5 ** 0.5) // 2)
        y = x + n
        if x <= 25 and y <= 25:
            pairs.add((x, y))
            pairs.add((y, x))
    if (a, b) in pairs:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
                continue
            na, nb = a - i, b - j
            key = (min(na, nb), max(na, nb))
            if key in pairs:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return "WIN " + str(best[0]) + " " + str(best[1])
