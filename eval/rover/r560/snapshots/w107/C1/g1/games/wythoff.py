def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            res = False
            for x in range(1, i + 1):
                if not win[i - x][j]:
                    res = True
                    break
            if not res:
                for y in range(1, j + 1):
                    if not win[i][j - y]:
                        res = True
                        break
            if not res:
                for t in range(1, min(i, j) + 1):
                    if not win[i - t][j - t]:
                        res = True
                        break
            win[i][j] = res

    if not win[a][b]:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and not win[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
