def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip()
        idx += 1
        cells = []
        for c in row[:w]:
            cells.append(1 if c == '#' else 0)
        while len(cells) < w:
            cells.append(0)
        grid.append(cells)
    for _ in range(k):
        new_grid = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            cnt += 1
                if grid[i][j]:
                    new_grid[i][j] = 1 if cnt in (2, 3) else 0
                else:
                    new_grid[i][j] = 1 if cnt == 3 else 0
        grid = new_grid
    out_rows = []
    for i in range(h):
        out_rows.append(''.join('#' if v else '.' for v in grid[i]))
    return '\n'.join(out_rows)
