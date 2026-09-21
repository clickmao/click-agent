def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip('\r')
        idx += 1
        cells = []
        for j in range(w):
            cells.append(1 if j < len(row) and row[j] == '#' else 0)
        grid.append(cells)
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
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
                    nxt[i][j] = 1 if (cnt == 2 or cnt == 3) else 0
                else:
                    nxt[i][j] = 1 if cnt == 3 else 0
        grid = nxt
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
