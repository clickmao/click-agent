"""康威生命游戏：H 代演化。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i].rstrip('\n')) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)


def _step(grid, h, w):
    new = [['.'] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and grid[yy][xx] == '#':
                        n += 1
            if grid[y][x] == '#':
                new[y][x] = '#' if (n == 2 or n == 3) else '.'
            else:
                new[y][x] = '#' if n == 3 else '.'
    return new
