"""Conway's Game of Life."""


def _step(grid, h, w):
    out = [[0] * w for _ in range(h)]
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
            out[r][c] = 1 if (grid[r][c] and n in (2, 3)) or ((not grid[r][c]) and n == 3) else 0
    return out


def solve(text):
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r].strip()] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
