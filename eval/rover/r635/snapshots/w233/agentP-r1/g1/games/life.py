"""Conway's Game of Life: k generations of evolution."""


def _step(grid, h, w):
    new = []
    for r in range(h):
        row_chars = []
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
            if alive and (n == 2 or n == 3):
                row_chars.append('#')
            elif (not alive) and n == 3:
                row_chars.append('#')
            else:
                row_chars.append('.')
        new.append(''.join(row_chars))
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = []
    for i in range(1, 1 + h):
        row = lines[i] if i < len(lines) else ''
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(row[:w])
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
