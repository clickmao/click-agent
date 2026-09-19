def solve(text):
    lines = text.split("\n")
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + r].rstrip()) for r in range(H)]

    def alive(g, r, c):
        if 0 <= r < H and 0 <= c < W:
            return g[r][c] == '#'
        return False

    for _ in range(k):
        nxt = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if alive(grid, r + dr, c + dc):
                            n += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if n in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt

    return "\n".join("".join(row) for row in grid)
