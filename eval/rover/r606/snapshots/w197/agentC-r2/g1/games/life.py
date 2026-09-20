"""Conway's Game of Life: evolve k generations."""


def _step(grid, h, w):
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
            alive = grid[r][c] == '#'
            if alive and (n == 2 or n == 3):
                row.append('#')
            elif (not alive) and n == 3:
                row.append('#')
            else:
                row.append('.')
        out.append(''.join(row))
    return out


def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [lines[1 + i] for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
