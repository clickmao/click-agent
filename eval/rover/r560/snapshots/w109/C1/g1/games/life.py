def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            count += 1
                if grid[y][x] == '#':
                    new[y][x] = '#' if count in (2, 3) else '.'
                else:
                    new[y][x] = '#' if count == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
