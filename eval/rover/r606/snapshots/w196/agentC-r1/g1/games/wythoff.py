def solve(text: str) -> str:
    vals = text.split()
    a, b = int(vals[0]), int(vals[1])
    beat = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            w = False
            for x in range(1, i + 1):
                if not beat[i - x][j]:
                    w = True
                    break
            if not w:
                for y in range(1, j + 1):
                    if not beat[i][j - y]:
                        w = True
                        break
            if not w:
                for t in range(1, min(i, j) + 1):
                    if not beat[i - t][j - t]:
                        w = True
                        break
            beat[i][j] = w
    if not beat[a][b]:
        return 'LOSE'
    best = None
    for i0 in range(0, a + 1):
        for j0 in range(0, b + 1):
            if i0 == 0 and j0 == 0:
                continue
            ok = (i0 > 0 and j0 == 0) or (i0 == 0 and j0 > 0) or (i0 == j0 and i0 > 0)
            if not ok:
                continue
            if not beat[a - i0][b - j0]:
                if best is None or (i0, j0) < best:
                    best = (i0, j0)
        if best is not None and best[0] == i0:
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
