def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    lose = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
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
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and (i == 0 or j == 0 or i == j) and lose[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
