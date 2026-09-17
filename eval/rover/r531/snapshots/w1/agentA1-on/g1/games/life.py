"""Conway's Game of Life: evolve the grid k generations.

Input (complete stdin text):
    line 1: H W k
    next H lines: W chars each, only '.' (dead) and '#' (alive)

Rules: simultaneous update, 8-neighbourhood, outside grid = dead.
Alive with 2 or 3 neighbours survives; dead with exactly 3 neighbours is born.

Output: the grid after k generations (k=0 -> the initial grid), H lines of W chars.
"""

from typing import List


def _step(grid: List[List[bool]], h: int, w: int) -> List[List[bool]]:
    """Return the next generation (simultaneous update, out-of-grid = dead)."""
    nxt: List[List[bool]] = [[False] * w for _ in range(h)]
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
                nxt[r][c] = n == 2 or n == 3
            else:
                nxt[r][c] = n == 3
    return nxt


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[ch == "#" for ch in lines[1 + r][:w]] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
