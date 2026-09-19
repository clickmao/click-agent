def solve(text: str) -> str:
    lines = text.strip("\n").splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(row.ljust(w, ".")[:w]) for row in lines[1:1 + h]]
    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            cnt += 1
                alive = grid[y][x] == "#"
                new[y][x] = "#" if (alive and cnt in (2, 3)) or (not alive and cnt == 3) else "."
        grid = new
    return "\n".join("".join(row) for row in grid)
