def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    h, w, k = map(int, lines[p].split())
    p += 1
    grid = []
    for i in range(h):
        row = lines[p + i] if p + i < len(lines) else ''
        grid.append(list(row[:w].ljust(w, '.')))
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            cnt += 1
                if grid[y][x] == '#':
                    new[y][x] = '#' if cnt in (2, 3) else '.'
                else:
                    new[y][x] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(r) for r in grid)
