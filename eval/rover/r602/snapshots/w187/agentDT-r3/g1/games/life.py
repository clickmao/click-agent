def solve(text):
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + r][:W]) for r in range(H)]
    for _ in range(k):
        ng = []
        for r in range(H):
            row = []
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    row.append('#' if (n == 2 or n == 3) else '.')
                else:
                    row.append('#' if n == 3 else '.')
            ng.append(''.join(row))
        grid = ng
    return '\n'.join(''.join(row) for row in grid)
