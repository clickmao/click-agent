"""Conway's Game of Life: H rows, W cols, k generations, torus-free (outside = dead)."""


def _step(grid, h, w):
    nxt = []
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
            alive = grid[r][c] == '#'
            if alive and n in (2, 3):
                row.append('#')
            elif (not alive) and n == 3:
                row.append('#')
            else:
                row.append('.')
        nxt.append(''.join(row))
    return nxt


def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = [lines[1 + i] for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
