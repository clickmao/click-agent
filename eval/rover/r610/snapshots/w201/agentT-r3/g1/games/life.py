def _step(grid, h, w):
    res = []
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
            if grid[y][x] == '#':
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        res.append(row)
    return res


def solve(text: str) -> str:
    lines = text.split('\n')
    parts = lines[0].split()
    h, w, k = int(parts[0]), int(parts[1]), int(parts[2])
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
