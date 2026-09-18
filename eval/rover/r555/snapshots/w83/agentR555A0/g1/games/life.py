"""Conway's Game of Life: evolve the grid exactly k generations."""


def _step(grid, h, w):
    out = []
    for r in range(h):
        row = []
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
                row.append('#' if (n == 2 or n == 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
