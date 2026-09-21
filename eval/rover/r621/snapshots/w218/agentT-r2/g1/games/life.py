"""Conway's Game of Life: evolve the grid k generations."""


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
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text):
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ''
        row = row.rstrip('\r')
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(row[:w])
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
