def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    parts = lines[idx].split()
    h, w, k = int(parts[0]), int(parts[1]), int(parts[2])
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ''
        row = row.rstrip('\r')
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(list(row[:w]))
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            cnt += 1
                if grid[i][j] == '#':
                    nxt[i][j] = '#' if cnt == 2 or cnt == 3 else '.'
                else:
                    nxt[i][j] = '#' if cnt == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(r) for r in grid)
