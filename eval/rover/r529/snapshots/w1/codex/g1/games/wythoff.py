def solve(text: str) -> str:
    a, b = map(int, text.split())
    lo, hi = min(a, b), max(a, b)
    # losing positions are (floor(n*phi), floor(n*phi^2))
    losing = set()
    n = 0
    while True:
        x = int(n * (1 + 5 ** 0.5) / 2)
        y = x + n
        if x > 25 and y > 25:
            break
        losing.add((x, y))
        n += 1
    if (lo, hi) in losing:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if (min(na, nb), max(na, nb)) in losing:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
