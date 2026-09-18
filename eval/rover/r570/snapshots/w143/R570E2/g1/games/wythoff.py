def solve(text: str) -> str:
    a, b = map(int, text.split())
    # P 位置（先手必败）: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    p = set()
    n = 0
    while True:
        x = int(n * phi)
        y = int(n * phi * phi)
        if x > 25 or y > 25:
            break
        p.add((x, y))
        n += 1
    if (min(a, b), max(a, b)) in p or (a, b) in [(0, 0)]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            key = (min(na, nb), max(na, nb))
            if key in p:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
