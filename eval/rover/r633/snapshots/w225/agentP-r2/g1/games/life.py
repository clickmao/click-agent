"""Conway's Game of Life: evolve a grid by k generations."""


def _step(grid, h, w):
    nxt = [[0] * w for _ in range(h)]
    for i in range(h):
        for j in range(w):
            live = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                        live += 1
            if grid[i][j]:
                nxt[i][j] = 1 if live in (2, 3) else 0
            else:
                nxt[i][j] = 1 if live == 3 else 0
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    ptr = 0
    while ptr < len(lines) and lines[ptr].strip() == '':
        ptr += 1
    h, w, k = (int(x) for x in lines[ptr].split())
    ptr += 1
    grid = [[1 if c == '#' else 0 for c in lines[ptr + i]] for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
