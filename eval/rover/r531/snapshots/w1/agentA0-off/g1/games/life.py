"""Conway's Game of Life: evolve an H x W grid for k generations.

stdin format:
    line 1: H W k        (1<=H,W<=20, 0<=k<=20)
    next H lines: W chars each, '.' = dead, '#' = alive
stdout:
    the grid after k generations (k=0 means the initial grid),
    H lines, W chars each.
"""

__all__ = ["solve"]


def _neighbours(grid, r, c, h, w):
    """Count live neighbours of (r, c); cells outside the grid are dead."""
    total = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                total += 1
    return total


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = _neighbours(grid, r, c, h, w)
                if grid[r][c] == "#":
                    new[r][c] = "#" if n in (2, 3) else "."
                else:
                    new[r][c] = "#" if n == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
