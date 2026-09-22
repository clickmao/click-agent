def solve(text: str) -> str:
    tokens = text.split()
    h = int(tokens[0])
    w = int(tokens[1])
    k = int(tokens[2])
    rows = tokens[3:3 + h]
    grid = [[c == '#' for c in row] for row in rows]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr = r + dr
                cc = c + dc
                if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                    cnt += 1
        return cnt

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c]:
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return "\n".join("".join('#' if cell else '.' for cell in row) for row in grid)
