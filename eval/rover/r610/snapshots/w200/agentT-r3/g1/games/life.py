"""Conway's Game of Life: H generations of evolution.

stdin format:
    H W k
    H lines of W chars each, '.', '#'
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    # first non-empty line holds H W k
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    h, w, k = map(int, lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ''
        idx += 1
        row = row.rstrip('\r\n')
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(list(row[:w]))

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            nb += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if nb in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if nb == 3 else '.'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
