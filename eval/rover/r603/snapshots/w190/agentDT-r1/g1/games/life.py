def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]

    def neighbours(g, r, c):
        n = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == '#':
                    n += 1
        return n

    for _ in range(k):
        nxt = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = neighbours(grid, r, c)
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if (n == 2 or n == 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
