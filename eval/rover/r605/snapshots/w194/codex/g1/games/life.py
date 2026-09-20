def _step(grid, H, W):
    out = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            row.append('#' if (n == 3 or (alive and n == 2)) else '.')
        out.append(row)
    return [''.join(row) for row in out]


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx].rstrip('\r') if idx < len(lines) else ''
        grid.append(row[:W].ljust(W, '.'))
        idx += 1
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
