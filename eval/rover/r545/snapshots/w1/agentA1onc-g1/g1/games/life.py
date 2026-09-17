"""Conway's Game of Life: H x W grid evolved k generations.

Input (complete stdin text)::

    H W k
    <H lines of W chars, each '.' (dead) or '#' (alive)>

Cells outside the grid are dead.  Each generation is applied *simultaneously*:
a live cell survives with 2 or 3 live neighbours, otherwise it dies; a dead
cell becomes alive with exactly 3 live neighbours.

Output: the grid after k generations (k == 0 gives the initial grid), H lines
of W characters, no trailing newline.
"""


def _step(grid, h, w):
    """Return the next generation of *grid* (list of list of 0/1)."""
    nxt = [[0] * w for _ in range(h)]
    for r in range(h):
        row = grid[r]
        for c in range(w):
            # Count the 8 neighbours, treating out-of-grid cells as dead.
            n = 0
            for dr in (-1, 0, 1):
                nr = r + dr
                if nr < 0 or nr >= h:
                    continue
                nrow = grid[nr]
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nc = c + dc
                    if nc < 0 or nc >= w:
                        continue
                    n += nrow[nc]
            if row[c]:
                nxt[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                nxt[r][c] = 1 if n == 3 else 0
    return nxt


def solve(text: str) -> str:
    """Evolve the grid for k generations and return the rendered result."""
    lines = text.splitlines()
    h, w, k = (int(t) for t in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r].strip()]
            for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
