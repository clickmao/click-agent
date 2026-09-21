"""Conway's Game of Life: evolve the grid by k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return ""
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[False] * w for _ in range(h)]
    for i in range(h):
        row = lines[i + 1] if i + 1 < len(lines) else ""
        for j in range(w):
            grid[i][j] = j < len(row) and row[j] == "#"

    for _ in range(k):
        new = [[False] * w for _ in range(h)]
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
                    new[i][j] = n == 2 or n == 3
                else:
                    new[i][j] = n == 3
        grid = new

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
