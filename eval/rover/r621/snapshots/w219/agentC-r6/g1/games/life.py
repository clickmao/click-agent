def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip('\n')
        rows = list(row.ljust(w, '.'))
        grid.append([c == '#' for c in rows[:w]])
        idx += 1
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            cnt += 1
                if grid[i][j]:
                    new[i][j] = cnt == 2 or cnt == 3
                else:
                    new[i][j] = cnt == 3
        grid = new
    out_lines = []
    for i in range(h):
        out_lines.append(''.join('#' if grid[i][j] else '.' for j in range(w)))
    return '\n'.join(out_lines)
