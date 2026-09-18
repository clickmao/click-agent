def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    a, b = map(int, lines[0].split())
    N = max(a, b) + 1

    # lose[x][y] = True iff the state (x, y) is a P-position (previous player wins).
    lose = [[False] * N for _ in range(N)]
    for x in range(N):
        for y in range(N):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            ok = True
            for i in range(1, x + 1):
                if lose[x - i][y]:
                    ok = False
                    break
            if ok:
                for j in range(1, y + 1):
                    if lose[x][y - j]:
                        ok = False
                        break
            if ok:
                for t in range(1, min(x, y) + 1):
                    if lose[x - t][y - t]:
                        ok = False
                        break
            lose[x][y] = ok

    if lose[a][b]:
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j == 0:
                ni, nj = a - i, b
            elif i == 0 and j > 0:
                ni, nj = a, b - j
            elif i == j:
                ni, nj = a - i, b - j
            else:
                continue
            if lose[ni][nj]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
