def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[0].strip() == '':
        lines.pop(0)
    a, b = map(int, lines[0].split())
    n = max(a, b) + 1
    lose = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            ok = False
            for x in range(1, i + 1):
                if lose[i - x][j]:
                    ok = True
                    break
            if not ok:
                for y in range(1, j + 1):
                    if lose[i][j - y]:
                        ok = True
                        break
            if not ok:
                t = min(i, j)
                for d in range(1, t + 1):
                    if lose[i - d][j - d]:
                        ok = True
                        break
            lose[i][j] = not ok
    if lose[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if lose[a - i][b - j]:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
