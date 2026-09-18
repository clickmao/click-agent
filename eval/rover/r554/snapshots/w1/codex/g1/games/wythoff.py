def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    n = max(a, b) + 2
    losing = [[False] * n for _ in range(n)]
    # losing[x][y] computed by increasing sum
    for s in range(0, 2 * n):
        for x in range(0, n):
            y = s - x
            if y < 0 or y >= n:
                continue
            win = False
            for i in range(1, x + 1):
                if losing[x - i][y]:
                    win = True
                    break
            if not win:
                for j in range(1, y + 1):
                    if losing[x][y - j]:
                        win = True
                        break
            if not win:
                for d in range(1, min(x, y) + 1):
                    if losing[x - d][y - d]:
                        win = True
                        break
            losing[x][y] = not win

    if losing[a][b]:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing[a - i][b - j]:
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN %d %d" % best
