def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r].strip()
        while len(row) < w:
            row += '.'
        grid.append(list(row[:w]))
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
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
                    new[r][c] = '#' if cnt == 2 or cnt == 3 else '.'
                else:
                    new[r][c] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
