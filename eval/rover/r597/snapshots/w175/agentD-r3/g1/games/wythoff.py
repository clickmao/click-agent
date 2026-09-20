def solve(text):
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            w = False
            for d in range(1, x + 1):
                if not win[x - d][y]:
                    w = True
                    break
            if not w:
                for d in range(1, y + 1):
                    if not win[x][y - d]:
                        w = True
                        break
            if not w:
                for d in range(1, min(x, y) + 1):
                    if not win[x - d][y - d]:
                        w = True
                        break
            win[x][y] = w
    if not win[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j == 0 and not win[a - i][b]:
                return 'WIN %d %d' % (i, j)
            if j > 0 and i == 0 and not win[a][b - j]:
                return 'WIN %d %d' % (i, j)
            if i > 0 and j > 0 and i == j and not win[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
