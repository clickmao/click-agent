"""Conway's Game of Life: H-row W-col grid evolved k generations.

solve(text) parses:
  line 1: H W k
  next H lines: W chars of '.' (dead) or '#' (alive)
and returns the grid after k generations (k=0 is the initial grid),
H lines of W chars, no trailing newline.

Rules: cells update simultaneously over the 8-neighbourhood; anything
outside the grid counts as dead. A live cell survives with 2 or 3 live
neighbours, otherwise dies; a dead cell with exactly 3 live neighbours
becomes alive.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                live = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            live += 1
                if grid[y][x] == '#':
                    new[y][x] = '#' if live in (2, 3) else '.'
                else:
                    new[y][x] = '#' if live == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
