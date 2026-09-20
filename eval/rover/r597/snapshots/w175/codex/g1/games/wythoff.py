def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    phi = (1 + 5 ** 0.5) / 2
    loses = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        if x > 25 and y > 25:
            break
        if x <= 25 and y <= 25:
            loses.add((x, y))
            loses.add((y, x))
        n += 1

    if (a, b) in loses:
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in loses:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
