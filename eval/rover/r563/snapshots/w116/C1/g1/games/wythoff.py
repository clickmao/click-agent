def solve(text: str) -> str:
    a, b = map(int, text.split())

    # losing positions are (floor(n*phi), floor(n*phi^2))
    losing = set()
    n = 0
    while True:
        x = int(n * 1.6180339887498949)
        y = int(n * 2.6180339887498949)
        if y > 25:
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
            if i == j or i == 0 or j == 0:
                if (a - i, b - j) in losing:
                    best = (i, j)
                    break
        if best is not None:
            break
    return "WIN %d %d" % best
