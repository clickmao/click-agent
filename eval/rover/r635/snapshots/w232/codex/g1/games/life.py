"""Conway's Game of Life: compute the grid after k generations."""


def _step(grid, h, w):
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                        n += 1
            alive = grid[y][x] == '#'
            if alive:
                row.append('#' if n == 2 or n == 3 else '.')
            else:
                row.append('#' if n == 3 else '.')
        out.append(''.join(row))
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(v) for v in lines[0].split())
    grid = [lines[1 + i].strip() for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
