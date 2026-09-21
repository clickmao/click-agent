def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    w = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            for t in range(1, i + 1):
                if not w[i - t][j]:
                    ok = True
                    break
            if not ok:
                for t in range(1, j + 1):
                    if not w[i][j - t]:
                        ok = True
                        break
            if not ok:
                for t in range(1, min(i, j) + 1):
                    if not w[i - t][j - t]:
                        ok = True
                        break
            w[i][j] = ok
    if not w[a][b]:
        return "LOSE"
    best = None
    for t in range(1, a + 1):
        if not w[a - t][b]:
            best = (t, 0)
            break
    if best is None:
        for t in range(1, b + 1):
            if not w[a][b - t]:
                best = (0, t)
                break
    if best is None:
        for t in range(1, min(a, b) + 1):
            if not w[a - t][b - t]:
                best = (t, t)
                break
    return "WIN " + str(best[0]) + " " + str(best[1])
