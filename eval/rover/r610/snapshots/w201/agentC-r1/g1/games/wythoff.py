def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    W = 30
    lose = [[False] * (W + 1) for _ in range(W + 1)]
    for i in range(W + 1):
        for j in range(W + 1):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            ok = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        ok = True
                        break
            lose[i][j] = not ok
    if lose[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if (i <= a and j == 0) or (j <= b and i == 0) or (i == j and i <= a and i <= b):
                if lose[ni][nj]:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
