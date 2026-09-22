"""Conway's Game of Life: simulate ``k`` generations and report the grid."""


def _step(grid, h, w):
    nxt = []
    for r in range(h):
        row = []
        for c in range(w):
            neighbours = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        neighbours += 1
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if neighbours in (2, 3) else '.')
            else:
                row.append('#' if neighbours == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip() if idx < len(lines) else ''
        idx += 1
        row = (row + '.' * w)[:w]
        grid.append(row)
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
