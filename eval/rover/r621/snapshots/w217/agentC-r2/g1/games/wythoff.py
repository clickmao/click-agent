def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    N = 25
    lose = [[False] * (N + 1) for _ in range(N + 1)]
    for x in range(N + 1):
        for y in range(N + 1):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            ok = False
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    ok = True
                    break
            if not ok:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        ok = True
                        break
            lose[x][y] = not ok
    if lose[a][b]:
        return "LOSE"
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 and j > 0) or (j == 0 and i > 0) or (i == j):
                cands.append((i, j))
    cands.sort()
    for (i, j) in cands:
        if lose[a - i][b - j]:
            return "WIN " + str(i) + " " + str(j)
    return "LOSE"
