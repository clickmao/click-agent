def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(h):
        row = lines[idx + 1 + r]
        row = (row + "." * w)[:w]
        grid.append(list(row))

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr = r + dr
                cc = c + dc
                if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == "#":
                    cnt += 1
        return cnt

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c] == "#":
                    if n == 2 or n == 3:
                        nxt[r][c] = "#"
                else:
                    if n == 3:
                        nxt[r][c] = "#"
        grid = nxt

    return "\n".join("".join(row) for row in grid)
