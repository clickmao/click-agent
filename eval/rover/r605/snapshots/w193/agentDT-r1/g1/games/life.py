def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    parts = lines[idx].split()
    idx += 1
    h, w, k = int(parts[0]), int(parts[1]), int(parts[2])
    grid = []
    for _ in range(h):
        grid.append(lines[idx].rstrip("\n"))
        idx += 1

    for _ in range(k):
        nxt = []
        for y in range(h):
            row = []
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
                if alive:
                    row.append("#" if cnt in (2, 3) else ".")
                else:
                    row.append("#" if cnt == 3 else ".")
            nxt.append("".join(row))
        grid = nxt

    return "\n".join(grid)
