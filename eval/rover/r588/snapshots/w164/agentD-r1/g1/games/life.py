def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\r\n")
        idx += 1
        cells = [False] * w
        for x in range(min(w, len(row))):
            cells[x] = row[x] == "#"
        grid.append(cells)

    def step(g):
        ng = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx]:
                            cnt += 1
                if g[y][x]:
                    ng[y][x] = cnt == 2 or cnt == 3
                else:
                    ng[y][x] = cnt == 3
        return ng

    for _ in range(k):
        grid = step(grid)

    out = []
    for y in range(h):
        out.append("".join("#" if grid[y][x] else "." for x in range(w)))
    return "\n".join(out)
