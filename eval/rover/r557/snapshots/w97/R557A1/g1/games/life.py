"""Conway's Game of Life: H-step evolution."""


def _parse(text):
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    return h, w, k, grid


def _step(h, w, grid):
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
        grid = _step(h, w, grid)
    return '\n'.join(''.join(row) for row in grid)
