def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    N = 30
    P = [[False] * (N + 1) for _ in range(N + 1)]
    for x in range(N + 1):
        for y in range(N + 1):
            if x == 0 and y == 0:
                continue
            lose = True
            for i in range(x + 1):
                for j in range(y + 1):
                    if i == 0 and j == 0:
                        continue
                    if i != 0 and j != 0 and i != j:
                        continue
                    if P[x - i][y - j]:
                        lose = False
                        break
                if not lose:
                    break
            P[x][y] = lose
    if P[a][b]:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if P[a - i][b - j]:
                best = (i, j)
                break
        if best:
            break
    return 'WIN %d %d' % best
