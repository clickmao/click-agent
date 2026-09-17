def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    # cold positions (P-positions): floor(n*phi), floor(n*phi^2)
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    n = 0
    while True:
        x = int(n * phi)
        y = x + n
        if x > 25 and y > 25:
            break
        cold.add((x, y))
        cold.add((y, x))
        n += 1
    if (a, b) in cold:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0) or ((i == 0 or j == 0)):
                if (a - i, b - j) in cold and (i == 0 or j == 0 or i == j):
                    return 'WIN %d %d' % (i, j)
    return 'WIN 0 0'
