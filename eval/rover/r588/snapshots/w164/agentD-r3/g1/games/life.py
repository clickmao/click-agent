def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for i in range(h):
        row = lines[idx + 1 + i]
        grid.append([c == '#' for c in row[:w]])
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    new[y][x] = cnt == 2 or cnt == 3
                else:
                    new[y][x] = cnt == 3
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
