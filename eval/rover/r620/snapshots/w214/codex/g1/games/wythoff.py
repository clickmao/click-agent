def solve(text: str) -> str:
    data = text.split()
    a = int(data[0]); b = int(data[1])
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            for t in range(1, i + 1):
                if not win[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if not win[i][j - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(i, j) + 1):
                    if not win[i - t][j - t]:
                        ok = True
                        break
            win[i][j] = ok
    if not win[a][b]:
        return 'LOSE'
    best = None
    for di in range(0, a + 1):
        for dj in range(0, b + 1):
            if di == 0 and dj == 0:
                continue
            if di > 0 and dj > 0 and di != dj:
                continue
            if di == 0 and dj == 0:
                continue
            if di > a or dj > b:
                continue
            if not win[a - di][b - dj]:
                best = (di, dj)
                break
        if best is not None:
            break
    di, dj = best
    return 'WIN %d %d' % (di, dj)
