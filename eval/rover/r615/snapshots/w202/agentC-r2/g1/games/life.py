"""Conway's Game of Life: H steps of evolution on a finite grid."""


def _step(grid, h, w):
    nxt = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        n += 1
            if grid[r][c]:
                nxt[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                nxt[r][c] = 1 if n == 3 else 0
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    rows = []
    while len(rows) < h:
        if idx >= len(lines):
            rows.append('')
            continue
        row = lines[idx].rstrip('\r')
        idx += 1
        if row == '' and len(rows) > 0:
            continue
        rows.append(row)
    grid = [[1 if ch == '#' else 0 for ch in rows[r][:w].ljust(w)] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
