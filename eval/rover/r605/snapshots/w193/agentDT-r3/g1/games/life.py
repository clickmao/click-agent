def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    def step(g):
        ng = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == "#":
                            cnt += 1
                if g[y][x] == "#":
                    ng[y][x] = "#" if cnt in (2, 3) else "."
                else:
                    ng[y][x] = "#" if cnt == 3 else "."
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
