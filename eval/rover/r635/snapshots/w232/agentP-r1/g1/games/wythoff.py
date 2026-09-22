def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    losing = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            res = True
            for i in range(1, x + 1):
                if losing[x - i][y]:
                    res = False
                    break
            if res:
                for j in range(1, y + 1):
                    if losing[x][y - j]:
                        res = False
                        break
            if res:
                for t in range(1, min(x, y) + 1):
                    if losing[x - t][y - t]:
                        res = False
                        break
            losing[x][y] = res

    if losing[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing[a - i][b - j]:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
