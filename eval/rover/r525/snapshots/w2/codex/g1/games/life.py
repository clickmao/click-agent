"""Conway's Game of Life evolution."""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    for _ in range(k):
        nxt = [["." for _ in range(w)] for _ in range(h)]
        for i in range(h):
            for j in range(w):
                neighbours = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == "#":
                            neighbours += 1
                if grid[i][j] == "#":
                    if neighbours == 2 or neighbours == 3:
                        nxt[i][j] = "#"
                elif neighbours == 3:
                    nxt[i][j] = "#"
        grid = nxt

    return "\n".join("".join(row) for row in grid)
