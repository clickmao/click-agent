def _parse(text):
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    h, w, k = map(int, lines[i].split())
    i += 1
    grid = []
    for r in range(h):
        while i < len(lines) and lines[i] == '':
            i += 1
        row = lines[i] if i < len(lines) else ''
        i += 1
        row = row.rstrip('\r')
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(list(row[:w]))
    return h, w, k, grid


def _step(grid, h, w):
    new = [['.'] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                new[r][c] = '#' if n in (2, 3) else '.'
            else:
                new[r][c] = '#' if n == 3 else '.'
    return new


def solve(text):
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
