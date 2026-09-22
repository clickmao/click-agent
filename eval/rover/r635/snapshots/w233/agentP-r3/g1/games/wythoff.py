def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    a, b = map(int, lines[0].split())
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
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
                for t in range(1, min(i, j) + 1):
                    if not win[i - t][j - t]:
                        ok = True
                        break
            win[i][j] = ok
    if not win[a][b]:
        return 'LOSE'
    best = None
    for i2 in range(a + 1):
        for j2 in range(b + 1):
            if i2 == 0 and j2 == 0:
                continue
            if i2 > 0 and j2 > 0 and i2 != j2:
                continue
            if not win[a - i2][b - j2]:
                cand = (i2, j2)
                if best is None or cand < best:
                    best = cand
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
