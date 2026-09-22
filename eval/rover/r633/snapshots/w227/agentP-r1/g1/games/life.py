def _step(grid, h, w):
    out = []
    for i in range(h):
        row = []
        for j in range(w):
            n = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    x = i + di
                    y = j + dj
                    if 0 <= x < h and 0 <= y < w and grid[x][y] == '#':
                        n += 1
            if grid[i][j] == '#':
                row.append('#' if n == 2 or n == 3 else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
