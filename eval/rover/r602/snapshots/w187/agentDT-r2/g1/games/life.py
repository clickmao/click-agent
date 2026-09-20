"""Conway's Game of Life: k-step evolution of an HxW grid."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ''
        row = row.rstrip('\r')
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(row[:w])
    for _ in range(k):
        nxt = []
        for r in range(h):
            cells = []
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
                    cells.append('#' if n in (2, 3) else '.')
                else:
                    cells.append('#' if n == 3 else '.')
            nxt.append(''.join(cells))
        grid = nxt
    return '\n'.join(grid)
