"""Wythoff game: decide lose positions and lexicographically smallest win move."""


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split()[:2])
    lim = 32
    lose = [[False] * (lim + 1) for _ in range(lim + 1)]
    for x in range(lim + 1):
        for y in range(lim + 1):
            if x == 0 and y == 0:
                lose[x][y] = True
                continue
            found = False
            for ny in range(y):
                if lose[x][ny]:
                    found = True
                    break
            if not found:
                for nx in range(x):
                    if lose[nx][y]:
                        found = True
                        break
            if not found:
                d = min(x, y)
                for t in range(1, d + 1):
                    if lose[x - t][y - t]:
                        found = True
                        break
            lose[x][y] = not found
    if lose[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            valid = False
            if i > 0 and j == 0:
                valid = True
            elif i == 0 and j > 0:
                valid = True
            elif i > 0 and j > 0 and i == j:
                valid = True
            if not valid:
                continue
            if lose[a - i][b - j]:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
