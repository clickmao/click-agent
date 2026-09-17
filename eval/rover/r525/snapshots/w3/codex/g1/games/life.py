"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines or not lines[0].strip():
        return ""
    h, w, k = (int(t) for t in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        x, y = i + di, j + dj
                        if 0 <= x < h and 0 <= y < w and grid[x][y] == "#":
                            n += 1
                if grid[i][j] == "#":
                    nxt[i][j] = "#" if n == 2 or n == 3 else "."
                else:
                    nxt[i][j] = "#" if n == 3 else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
