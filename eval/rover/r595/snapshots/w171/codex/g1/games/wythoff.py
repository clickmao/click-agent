def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    win = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                win[i][j] = False
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
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and (i == 0 or j == 0 or i == j):
                if not win[a - i][b - j]:
                    return "WIN %d %d" % (i, j)
