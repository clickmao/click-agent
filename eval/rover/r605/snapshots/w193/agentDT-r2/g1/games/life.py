def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    def step(g):
        nxt = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and g[yy][xx] == "#":
                            n += 1
                if g[y][x] == "#":
                    nxt[y][x] = "#" if n in (2, 3) else "."
                else:
                    nxt[y][x] = "#" if n == 3 else "."
        return nxt

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
