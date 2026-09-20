def solve(text: str) -> str:
    a, b = map(int, text.split())
    losing = set()
    for m in range(0, 60):
        x = (m * (1 + 5 ** 0.5) // 2)
        losing.add((x, x + m))
        losing.add((x + m, x))
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
