def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    def neighbors(i, j):
        cnt = 0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                    cnt += 1
        return cnt

    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                nb = neighbors(i, j)
                if grid[i][j] == '#':
                    new[i][j] = '#' if nb in (2, 3) else '.'
                else:
                    new[i][j] = '#' if nb == 3 else '.'
        grid = new

    return "\n".join("".join(row) for row in grid)
