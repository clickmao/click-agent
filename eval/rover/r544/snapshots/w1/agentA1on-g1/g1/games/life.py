"""Conway's Game of Life: advance the grid H generations.

Input format (complete stdin text)::

    H W k
    <H rows, each W chars of '.' (dead) or '#' (alive)>

Cells update *simultaneously* using the 8-neighbourhood; anything outside the
grid counts as dead.  Output: the grid after ``k`` generations, ``H`` rows of
``W`` characters, no trailing newline.
"""

from __future__ import annotations

ALIVE = "#"
DEAD = "."


def _step(grid: list[list[bool]], h: int, w: int) -> list[list[bool]]:
    """Return the next generation (8-neighbour, out-of-bounds = dead)."""
    nxt = [[False] * w for _ in range(h)]
    for r in range(h):
        row = grid[r]
        for c in range(w):
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
                    if nrow[nc]:
                        n += 1
            if row[c]:
                nxt[r][c] = n == 2 or n == 3
            else:
                nxt[r][c] = n == 3
    return nxt


def solve(text: str) -> str:
    """Evolve the Life grid ``k`` generations and render the result."""
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[ch == ALIVE for ch in lines[1 + r].strip()] for r in range(h)]

    for _ in range(k):
        grid = _step(grid, h, w)

    return "\n".join(
        "".join(ALIVE if cell else DEAD for cell in row) for row in grid
    )
