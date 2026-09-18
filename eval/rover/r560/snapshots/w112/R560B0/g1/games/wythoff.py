def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    alive = [[True] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            winnable = False
            for t in range(1, i + 1):
                if not alive[i - t][j]:
                    winnable = True
                    break
            if not winnable:
                for t in range(1, j + 1):
                    if not alive[i][j - t]:
                        winnable = True
                        break
            if not winnable:
                for t in range(1, min(i, j) + 1):
                    if not alive[i - t][j - t]:
                        winnable = True
                        break
            alive[i][j] = winnable
    if not alive[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if not alive[ni][nj] and not (i and j and i != j):
                if i == 0 or j == 0 or i == j:
                    if best is None or (i, j) < best:
                        best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
