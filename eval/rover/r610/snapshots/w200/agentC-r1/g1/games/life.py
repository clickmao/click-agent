"""Conway's Game of Life: H x W grid, k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    first = lines[idx].split()
    idx += 1
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = []
    while len(rows) < h and idx < len(lines):
        row = lines[idx].strip()
        idx += 1
        if row:
            rows.append(row)
    grid = [list(row[:w].ljust(w, '.')) for row in rows]

    def step(g):
        ng = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == '#':
                            n += 1
                alive = g[y][x] == '#'
                if alive and n in (2, 3):
                    ng[y][x] = '#'
                elif (not alive) and n == 3:
                    ng[y][x] = '#'
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
