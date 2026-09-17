"""Conway's Game of Life: evolve the grid k generations.

stdin:
    line 1: H W k      (1<=H,W<=20, 0<=k<=20)
    next H lines: W chars each, '.' = dead, '#' = alive

Rules (all cells updated simultaneously, 8-neighbourhood, outside = dead):
    alive with 2 or 3 neighbours survives, else dies
    dead with exactly 3 neighbours becomes alive

stdout: H lines of W chars, the generation-k grid (no trailing newline).
"""


def _step(grid, h, w):
    """Return the next generation as a list of list-of-chars."""
    out = [["."] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        n += 1
            if grid[r][c] == "#":
                out[r][c] = "#" if n in (2, 3) else "."
            else:
                out[r][c] = "#" if n == 3 else "."
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join(row) for row in grid)
