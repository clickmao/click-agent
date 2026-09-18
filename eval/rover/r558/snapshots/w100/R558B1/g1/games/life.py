"""Conway's Game of Life."""


def solve(text):
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append(list(row[:w]))
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
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
                    new[r][c] = '#' if n == 2 or n == 3 else '.'
                else:
                    new[r][c] = '#' if n == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
