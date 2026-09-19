"""Wythoff's game."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    limit = 25
    n = limit + 1
    lose = [[False] * n for _ in range(n)]
    for x in range(n):
        for y in range(n):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            found_move = False
            i = 1
            while x - i >= 0:
                if lose[x - i][y]:
                    found_move = True
                    break
                i += 1
            if not found_move:
                j = 1
                while y - j >= 0:
                    if lose[x][y - j]:
                        found_move = True
                        break
                    j += 1
            if not found_move:
                t = 1
                while x - t >= 0 and y - t >= 0:
                    if lose[x - t][y - t]:
                        found_move = True
                        break
                    t += 1
            lose[x][y] = not found_move
    if lose[a][b]:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            nx, ny = a - i, b - j
            if lose[nx][ny]:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
