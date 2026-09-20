def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    h, w, k = map(int, lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([1 if c == '#' else 0 for c in row])
    for _ in range(k):
        ngrid = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    ngrid[r][c] = 1 if (cnt == 2 or cnt == 3) else 0
                else:
                    ngrid[r][c] = 1 if cnt == 3 else 0
        grid = ngrid
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
