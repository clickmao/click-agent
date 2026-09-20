def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lose = set()
    n = 0
    while True:
        x = (n * (1 + 5 ** 0.5)) // 2
        while int(x) * int(x) != x * x or x != int(x):
            break
        x = int(x)
        y = x + n
        if x > a and x > b and y > a and y > b:
            break
        lose.add((x, y))
        lose.add((y, x))
        n += 1
        if x > 30 and y > 30:
            break
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (na, nb) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
        if best is not None and best[0] == i:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
