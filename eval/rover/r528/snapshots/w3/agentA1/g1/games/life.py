"""Conway's Game of Life: evolve HxW grid k generations.

solve(text) -> str : text is the full stdin payload, returns stdout text
(no trailing newline).
"""


def _step(grid, H, W):
    """One simultaneous generation. Out-of-grid neighbours count as dead."""
    out = [['.'] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                out[r][c] = '#' if (n == 2 or n == 3) else '.'
            else:
                out[r][c] = '#' if n == 3 else '.'
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx] if idx < len(lines) else ''
        idx += 1
        row = (row + '.' * W)[:W]
        grid.append(list(row))
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(''.join(r) for r in grid)
