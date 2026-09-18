def solve(text: str) -> str:
    a, b = map(int, text.split())
    LIM = 60
    losing = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    for x in range(LIM + 1):
        for y in range(LIM + 1):
            if x == 0 and y == 0:
                losing[x][y] = True
                continue
            w = False
            for i in range(1, x + 1):
                if losing[x - i][y]:
                    w = True
                    break
            if not w:
                for j in range(1, y + 1):
                    if losing[x][y - j]:
                        w = True
                        break
            if not w:
                for t in range(1, min(x, y) + 1):
                    if losing[x - t][y - t]:
                        w = True
                        break
            losing[x][y] = not w
    if losing[a][b]:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
