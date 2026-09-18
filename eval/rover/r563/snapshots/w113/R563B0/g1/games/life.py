def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    grid = []
    for r in range(1, h + 1):
        row = lines[idx + r] if idx + r < len(lines) else ''
        row = row.ljust(w, '.')[:w]
        grid.append([1 if c == '#' else 0 for c in row])
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w:
                            n += grid[ni][nj]
                if grid[i][j]:
                    ng[i][j] = 1 if n == 2 or n == 3 else 0
                else:
                    ng[i][j] = 1 if n == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
