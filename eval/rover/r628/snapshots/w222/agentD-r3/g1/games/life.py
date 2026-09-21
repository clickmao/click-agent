def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i][:w]
        row = row + '.' * (w - len(row))
        grid.append(list(row))
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            n += 1
                if grid[i][j] == '#':
                    new[i][j] = '#' if n == 2 or n == 3 else '.'
                else:
                    new[i][j] = '#' if n == 3 else '.'
        grid = new
    return '\n'.join(''.join(r) for r in grid)
