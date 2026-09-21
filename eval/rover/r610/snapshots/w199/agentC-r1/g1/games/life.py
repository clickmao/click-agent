"""Conway's Game of Life.

stdin format:
    line 1: H W k
    next H lines: W chars, '.' (dead) or '#' (alive)

Output: grid after k generations, H lines of W chars, no trailing newline.
Synchronous update with 8-neighbourhood; outside the grid counts as dead.
"""


def _step(grid, h, w):
    new = [['.' for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                        n += 1
            if grid[y][x] == '#':
                new[y][x] = '#' if n in (2, 3) else '.'
            else:
                new[y][x] = '#' if n == 3 else '.'
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(t) for t in lines[0].split()[:3])
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
