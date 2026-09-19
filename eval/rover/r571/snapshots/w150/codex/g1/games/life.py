def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and grid[yy][xx] == "#":
                            n += 1
                if grid[y][x] == "#":
                    new[y][x] = "#" if n in (2, 3) else "."
                else:
                    new[y][x] = "#" if n == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
