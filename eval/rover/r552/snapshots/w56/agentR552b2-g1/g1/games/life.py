def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = ""
        while len(row) < w:
            row += lines[idx]
            idx += 1
        grid.append(list(row[:w]))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            cnt += 1
                if grid[y][x] == "#":
                    nxt[y][x] = "#" if cnt in (2, 3) else "."
                else:
                    nxt[y][x] = "#" if cnt == 3 else "."
        grid = nxt
    return "\n".join("".join(r) for r in grid)
