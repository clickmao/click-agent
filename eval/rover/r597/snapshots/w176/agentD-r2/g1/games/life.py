"""Conway's Game of Life: evolve a grid k generations."""


def step(grid, h, w):
    out = [['.'] * w for _ in range(h)]
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
                out[i][j] = '#' if cnt == 2 or cnt == 3 else '.'
            else:
                out[i][j] = '#' if cnt == 3 else '.'
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = map(int, lines[0].split())
    grid = [list(line.ljust(w, '.')[:w]) for line in lines[1:1 + h]]
    for _ in range(k):
        grid = step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
