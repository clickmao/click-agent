def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    N = 64
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    lose[0][0] = True
    for x in range(N + 1):
        for y in range(x, N + 1):
            if x == 0 and y == 0:
                continue
            w = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    w = True
                    break
            if not w:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        w = True
                        break
            if not w:
                for d in range(1, min(x, y) + 1):
                    if lose[x - d][y - d]:
                        w = True
                        break
            lose[x][y] = not w
            lose[y][x] = lose[x][y]
    if lose[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        na, nb = a - i, b
        if lose[na][nb] and (best is None or (i, 0) < best):
            best = (i, 0)
    for j in range(1, b + 1):
        na, nb = a, b - j
        if lose[na][nb] and (best is None or (0, j) < best):
            best = (0, j)
    for d in range(1, min(a, b) + 1):
        na, nb = a - d, b - d
        if lose[na][nb] and (best is None or (d, d) < best):
            best = (d, d)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
