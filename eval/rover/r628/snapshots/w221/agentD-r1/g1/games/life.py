def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            cnt += 1
                if grid[y][x] == "#":
                    nxt[y][x] = "#" if cnt in (2, 3) else "."
                else:
                    nxt[y][x] = "#" if cnt == 3 else "."
        grid = nxt
    return "\n".join("".join(r) for r in grid)
