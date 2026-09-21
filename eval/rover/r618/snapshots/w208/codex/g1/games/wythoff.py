def solve(text: str) -> str:
    a, b = map(int, text.split())

    win = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            w = False
            for i in range(1, x + 1):
                if not win[x - i][y]:
                    w = True
                    break
            if not w:
                for j in range(1, y + 1):
                    if not win[x][y - j]:
                        w = True
                        break
            if not w and x >= 1 and y >= 1:
                for t in range(1, min(x, y) + 1):
                    if not win[x - t][y - t]:
                        w = True
                        break
            win[x][y] = w

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not win[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
