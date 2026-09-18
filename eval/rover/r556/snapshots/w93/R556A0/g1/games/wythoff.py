def solve(text):
    a, b = map(int, text.split()[:2])
    N = 40
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        for j in range(N + 1):
            if i == 0 and j == 0:
                lose[i][j] = True
            else:
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
                if not ok:
                    lose[i][j] = True
    if lose[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ni = a - i
            nj = b - j
            if lose[ni][nj]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
