"""Conway's Game of Life: evolve the grid for k generations."""


def solve(text):
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split()[:3])
    grid = lines[1:1 + h]
    for _ in range(k):
        nxt = []
        for y in range(h):
            row = []
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            cnt += 1
                alive = grid[y][x] == '#'
                if alive:
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            nxt.append(''.join(row))
        grid = nxt
    return '\n'.join(grid)
