"""Conway's Game of Life: H generations evolution."""


def _evolve(grid, h, w):
    new = [['.' for _ in range(w)] for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                new[r][c] = '#' if n in (2, 3) else '.'
            else:
                new[r][c] = '#' if n == 3 else '.'
    return new


def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i].ljust(w)) for i in range(h)]
    for _ in range(k):
        grid = _evolve(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
