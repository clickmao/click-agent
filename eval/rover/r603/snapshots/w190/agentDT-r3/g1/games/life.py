def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[lines[1 + i][j] == '#' for j in range(w)] for i in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                c = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            c += 1
                nxt[i][j] = (c == 2 or c == 3) if grid[i][j] else (c == 3)
        grid = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
