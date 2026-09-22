def _neighbours(grid, r, c, H, W):
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == '#':
                count += 1
    return count


def _step(grid, H, W):
    nxt = []
    for r in range(H):
        row = []
        for c in range(W):
            alive = grid[r][c] == '#'
            n = _neighbours(grid, r, c, H, W)
            if alive:
                row.append('#' if n == 2 or n == 3 else '.')
            else:
                row.append('#' if n == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i][:W] for i in range(H)]
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
