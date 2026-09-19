def solve(text):
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W:
                    if g[rr][cc] == '#':
                        cnt += 1
        return cnt

    for _ in range(k):
        ng = [[('#' if (grid[r][c] == '#' and neighbors(grid, r, c) in (2, 3)) or (grid[r][c] == '.' and neighbors(grid, r, c) == 3) else '.') for c in range(W)] for r in range(H)]
        grid = ng

    return '\n'.join(''.join(row) for row in grid)
