def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        new = [["."] * w for _ in range(h)]
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
                    new[i][j] = "#" if n in (2, 3) else "."
                else:
                    new[i][j] = "#" if n == 3 else "."
        grid = new
    return "\n".join("".join(row) for row in grid)
