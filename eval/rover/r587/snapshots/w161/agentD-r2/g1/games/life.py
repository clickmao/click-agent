def _step(grid, h, w):
    nxt = [['.' for _ in range(w)] for _ in range(h)]
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
                nxt[r][c] = '#' if (n == 2 or n == 3) else '.'
            else:
                nxt[r][c] = '#' if n == 3 else '.'
    return nxt


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < h and idx < len(lines):
        row = lines[idx]
        idx += 1
        if row.strip() == '' and len(row) != w:
            continue
        grid.append(list((row + '.' * w)[:w]))
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
