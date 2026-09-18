def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    n = max(a, b)
    losing = set()
    pairs = []
    for k in range(0, n + 1):
        x = (k * (1 + 5 ** 0.5) / 2)
        x = int(x + 0.5)
        y = x + k
        if x > n or y > n:
            break
        pairs.append((x, y))
    for (x, y) in pairs:
        if (a, b) == (x, y) or (a, b) == (y, x):
            return 'LOSE'
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if na == 0 and nb == 0:
                moves.append((i, j))
                continue
            lose = False
            for (x, y) in pairs:
                if (na, nb) == (x, y) or (na, nb) == (y, x):
                    lose = True
                    break
            if lose:
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN %d %d' % (i, j)
