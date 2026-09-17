def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    h, w, k = int(tokens[0]), int(tokens[1]), int(tokens[2])
    rows = tokens[3:3 + h]
    grid = [list(r.ljust(w, ".")) for r in rows]
    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            c += 1
                if grid[y][x] == "#":
                    new[y][x] = "#" if c in (2, 3) else "."
                else:
                    new[y][x] = "#" if c == 3 else "."
        grid = new
    return "\n".join("".join(r) for r in grid)
