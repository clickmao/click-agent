def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    n = max(a, b) + 1

    win = [[False] * n for _ in range(n)]
    for i in range(1, a + 1):
        for j in range(1, b + 1):
            ok = False
            for x in range(1, i + 1):
                if not win[i - x][j]:
                    ok = True
                    break
            if not ok:
                for y in range(1, j + 1):
                    if not win[i][j - y]:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(i, j) + 1):
                    if not win[i - d][j - d]:
                        ok = True
                        break
            win[i][j] = ok

    if not win[a][b]:
        return 'LOSE'

    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j == 0:
                nxt = (a - i, b)
            elif j > 0 and i == 0:
                nxt = (a, b - j)
            elif i == j and i > 0:
                nxt = (a - i, b - j)
            else:
                continue
            if not win[nxt[0]][nxt[1]]:
                moves.append((i, j))

    i, j = min(moves)
    return 'WIN %d %d' % (i, j)
