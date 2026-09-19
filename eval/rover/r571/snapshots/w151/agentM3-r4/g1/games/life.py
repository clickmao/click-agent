def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = [int(x) for x in lines[idx].split()]
    idx += 1
    grid = []
    for r in range(h):
        grid.append(list(lines[idx + r].rstrip('\r')))
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    ng[r][c] = '#' if cnt == 2 or cnt == 3 else '.'
                else:
                    ng[r][c] = '#' if cnt == 3 else '.'
        grid = ng
    return '\n'.join(''.join(row) for row in grid)
