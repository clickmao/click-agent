def solve(text: str) -> str:
    lines = text.split('\n')
    a, b = map(int, lines[0].split())
    N = 26
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for u in range(N + 1):
        for v in range(N + 1):
            w = False
            for i in range(u + 1):
                if i > 0 and not lose[u - i][v]:
                    w = True
                    break
            if not w:
                for j in range(v + 1):
                    if j > 0 and not lose[u][v - j]:
                        w = True
                        break
            if not w:
                for d in range(1, min(u, v) + 1):
                    if not lose[u - d][v - d]:
                        w = True
                        break
            lose[u][v] = not w
    if lose[a][b]:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and lose[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
