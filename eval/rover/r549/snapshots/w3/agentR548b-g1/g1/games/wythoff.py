def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    N = 25

    def is_losing(x, y):
        for i in range(x + 1):
            for j in range(y + 1):
                for d in (1, 1):
                    pass
        return False

    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for x in range(N + 1):
        for y in range(N + 1):
            if x == 0 and y == 0:
                lose[0][0] = True
                continue
            ok = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    ok = True
                    break
            if not ok:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        ok = True
                        break
            if not ok:
                d = 1
                while d <= x and d <= y:
                    if lose[x - d][y - d]:
                        ok = True
                        break
                    d += 1
            lose[x][y] = not ok
    if lose[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0) or (i == j):
                na, nb = a - i, b - j
                if na >= 0 and nb >= 0 and lose[na][nb]:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
