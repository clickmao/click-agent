"""Conway's Game of Life: evolve the initial grid H rows x W cols for k generations."""


def _step(grid, h, w):
    nxt = [[0] * w for _ in range(h)]
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
                nxt[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                nxt[r][c] = 1 if n == 3 else 0
    return nxt


def solve(text):
    lines = text.splitlines()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
