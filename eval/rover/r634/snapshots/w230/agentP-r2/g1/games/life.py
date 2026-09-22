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
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            if alive and (n == 2 or n == 3):
                row.append('#')
            elif (not alive) and n == 3:
                row.append('#')
            else:
                row.append('.')
        out.append(''.join(row))
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    H, W, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i]) for i in range(H)]
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(''.join(r) for r in grid)
