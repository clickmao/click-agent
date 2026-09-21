"""Conway's Game of Life: H rows x W cols, evolve k generations."""


def step(grid, h, w):
    nxt = [['.'] * w for _ in range(h)]
    for i in range(h):
        for j in range(w):
            cnt = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni = i + di
                    nj = j + dj
                    if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                        cnt += 1
            if grid[i][j] == '#':
                nxt[i][j] = '#' if cnt in (2, 3) else '.'
            else:
                nxt[i][j] = '#' if cnt == 3 else '.'
    return nxt


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        row = (row + "." * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        grid = step(grid, h, w)
    return "\n".join("".join(r) for r in grid)
