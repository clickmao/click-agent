"""Conway's Game of Life: H-generation evolution.

Input format:
    line 1: H W k   (1<=H,W<=20, 0<=k<=20)
    next H lines: W characters each, '.' = dead, '#' = alive

Output: the grid after k generations, H lines of W characters.
Rules: simultaneous 8-neighbour update; outside the grid is always dead;
       a live cell survives iff it has 2 or 3 live neighbours;
       a dead cell becomes alive iff it has exactly 3 live neighbours.
"""


def _step(grid):
    h = len(grid)
    w = len(grid[0])
    out = []
    for r in range(h):
        row = []
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
            if grid[r][c] == '#':
                row.append('#' if (n == 2 or n == 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx].rstrip('\n')
        idx += 1
        row = (row + '.' * w)[:w]
        grid.append(row)
    for _ in range(k):
        grid = _step(grid)
    return '\n'.join(grid)
