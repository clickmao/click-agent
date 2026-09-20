def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    N = 25
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for x in range(N + 1):
        for y in range(N + 1):
            if x == 0 and y == 0:
                continue
            res = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    res = True
                    break
            if not res:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        res = True
                        break
            if not res:
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        res = True
                        break
            lose[x][y] = res
    if lose[a][b]:
        return 'LOSE'
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if lose[a - i][b - j]:
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN %d %d' % (i, j)
