"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split()[:3])
    idx += 1
    grid = []
    while len(grid) < h:
        if idx >= len(lines):
            grid.append(['.'] * w)
            continue
        row = lines[idx]
        idx += 1
        row = row.rstrip('\r').ljust(w, '.')[:w]
        grid.append(list(row))

    height = len(grid)
    width = len(grid[0]) if height else 0

    def step(g):
        ng = [[False] * width for _ in range(height)]
        for r in range(height):
            for c in range(width):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < height and 0 <= cc < width and g[rr][cc]:
                            n += 1
                alive = g[r][c]
                ng[r][c] = (n == 2 or n == 3) if alive else (n == 3)
        return ng

    live = [[ch == '#' for ch in row] for row in grid]
    for _ in range(k):
        live = step(live)

    return '\n'.join(''.join('#' if x else '.' for x in row) for row in live)
