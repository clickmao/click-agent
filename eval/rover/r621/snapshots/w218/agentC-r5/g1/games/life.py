def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[ch == '#' for ch in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            c += 1
                ng[y][x] = c == 3 or (c == 2 and grid[y][x])
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
