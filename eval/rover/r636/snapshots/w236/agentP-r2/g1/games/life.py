"""Conway's Game of Life: H generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(1, h + 1):
        row = lines[idx + r]
        grid.append(list(row[:w].ljust(w, '.')))

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
                    new[i][j] = '#' if n in (2, 3) else '.'
                else:
                    new[i][j] = '#' if n == 3 else '.'
        grid = new

    return '\n'.join(''.join(row) for row in grid)
