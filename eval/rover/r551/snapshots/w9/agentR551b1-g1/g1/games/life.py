def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < h:
        row = lines[idx] if idx < len(lines) else ''
        idx += 1
        if row == '' and len(grid) == 0 and idx >= len(lines):
            break
        row = row.rstrip('\r')
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[y][x] = cnt == 2 or cnt == 3
                else:
                    nxt[y][x] = cnt == 3
        grid = nxt
    out = []
    for y in range(h):
        out.append(''.join('#' if c else '.' for c in grid[y]))
    return '\n'.join(out)
