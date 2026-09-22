"""Conway's Game of Life: H rows x W cols, k generations."""


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(line.ljust(w, '.')) for line in lines[1:1 + h]]
    while len(grid) < h:
        grid.append(['.'] * w)
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            cnt += 1
                if grid[i][j] == '#':
                    new[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    new[i][j] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
