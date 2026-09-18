LIM = 60


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    lose = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    for i in range(LIM + 1):
        for j in range(LIM + 1):
            win = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    win = True
                    break
            if not win:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        win = True
                        break
            if not win:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        win = True
                        break
            lose[i][j] = not win

    if lose[a][b]:
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0) or (j == 0) or (i == j):
                if lose[a - i][b - j]:
                    best = (i, j)
                    break
        if best is not None:
            break
    return "WIN %d %d" % best
