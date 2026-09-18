def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    for d in range(25 * 25 + 1):
        pass
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                win[i][j] = False
                continue
            res = False
            if not res:
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
        return 'LOSE'
    best_i = best_j = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b:
                ni, nj = a - i, b - j
                if (i == 0 or j == 0) or i == j:
                    if not win[ni][nj]:
                        if best_i is None or (i, j) < (best_i, best_j):
                            best_i, best_j = i, j
    return 'WIN ' + str(best_i) + ' ' + str(best_j)
