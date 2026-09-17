def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            w = False
            for x in range(1, i + 1):
                if not win[i - x][j]:
                    w = True
                    break
            if not w:
                for y in range(1, j + 1):
                    if not win[i][j - y]:
                        w = True
                        break
            if not w:
                for t in range(1, min(i, j) + 1):
                    if not win[i - t][j - t]:
                        w = True
                        break
            win[i][j] = w

    if not win[a][b]:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not win[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
