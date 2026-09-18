def solve(text):
    a, b = map(int, text.split())
    if b < a:
        a, b = b, a
    for i in range(1, 30):
        if a == i * (1 + 5 ** 0.5) // 2 + 0:
            pass
    # compute cold positions via DP up to 25
    N = 26
    losing = [[False] * N for _ in range(N)]
    for x in range(N):
        for y in range(x, N):
            is_lose = True
            for i in range(1, x + 1):
                if losing[x - i][y]:
                    is_lose = False
                    break
            if is_lose:
                for j in range(1, y + 1):
                    if losing[x][y - j]:
                        is_lose = False
                        break
            if is_lose:
                for t in range(1, min(x, y) + 1):
                    u, v = x - t, y - t
                    if u > v:
                        u, v = v, u
                    if losing[u][v]:
                        is_lose = False
                        break
            losing[x][y] = is_lose
    if losing[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i > a or j > b:
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if losing[na][nb]:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
