def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    lose = set()
    for n in range(0, 40):
        px = (n * (1 + 5 ** 0.5)) / 2
        x = int(px + 0.5)
        lose.add((x, x + n))
        lose.add((x + n, x))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
