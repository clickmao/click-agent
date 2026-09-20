"""Conway's Game of Life: evolve HxW grid by k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i].strip()
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            n += 1
                if grid[i][j]:
                    nxt[i][j] = n in (2, 3)
                else:
                    nxt[i][j] = n == 3
        grid = nxt
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
