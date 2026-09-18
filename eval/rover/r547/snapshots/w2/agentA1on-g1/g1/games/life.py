"""Conway's Game of Life, evolve k generations."""

from typing import List


def _step(grid: List[List[str]]) -> List[List[str]]:
    """One simultaneous generation update; out-of-grid cells are dead."""
    h = len(grid)
    w = len(grid[0]) if h else 0
    out = [['.'] * w for _ in range(h)]
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
                out[r][c] = '#' if (n == 2 or n == 3) else '.'
            else:
                out[r][c] = '#' if n == 3 else '.'
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i].strip()) for i in range(h)]
    for _ in range(k):
        grid = _step(grid)
    return '\n'.join(''.join(row) for row in grid)
