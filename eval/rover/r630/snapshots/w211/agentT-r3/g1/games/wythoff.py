def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    N = 60
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for x in range(N + 1):
        for y in range(N + 1):
            good = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    good = True
                    break
            if not good:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        good = True
                        break
            if not good:
                d = min(x, y)
                for t in range(1, d + 1):
                    if lose[x - t][y - t]:
                        good = True
                        break
            lose[x][y] = not good
    if lose[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if lose[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
