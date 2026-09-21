def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    # Exact DP: P[x][y] is True iff (x, y) is a losing position for the player to move.
    P = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                P[x][y] = True
                continue
            reach = False
            for i in range(1, x + 1):
                if P[x - i][y]:
                    reach = True
                    break
            if not reach:
                for j in range(1, y + 1):
                    if P[x][y - j]:
                        reach = True
                        break
            if not reach:
                for t in range(1, min(x, y) + 1):
                    if P[x - t][y - t]:
                        reach = True
                        break
            P[x][y] = not reach

    if P[a][b]:
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if P[a - i][b - j] and (best is None or (i, j) < best):
                best = (i, j)
    return "WIN %d %d" % best
