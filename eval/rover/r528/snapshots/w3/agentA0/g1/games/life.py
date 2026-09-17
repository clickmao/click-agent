"""Conway's Game of Life: evolve H rows x W cols grid for k generations.

Rules: 8-neighbourhood, simultaneous update, out-of-grid cells are dead.
  live cell survives iff 2 or 3 live neighbours, else dies;
  dead cell becomes alive iff exactly 3 live neighbours.
"""


def _step(grid, h, w):
    """One simultaneous generation; returns a new grid (list of list of 0/1)."""
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            r0 = r - 1 if r > 0 else 0
            r1 = r + 2 if r + 2 <= h else h
            c0 = c - 1 if c > 0 else 0
            c1 = c + 2 if c + 2 <= w else w
            for rr in range(r0, r1):
                row = grid[rr]
                for cc in range(c0, c1):
                    if rr == r and cc == c:
                        continue
                    n += row[cc]
            out[r][c] = 1 if (grid[r][c] == 1 and (n == 2 or n == 3)) or \
                             (grid[r][c] == 0 and n == 3) else 0
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r].strip()] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
