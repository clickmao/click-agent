def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())

    lose = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            w = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    w = True
                    break
            if not w:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        w = True
                        break
            if not w:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        w = True
                        break
            lose[i][j] = not w

    if lose[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if lose[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
