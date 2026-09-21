def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = map(int, lines[0].split())
    grid = [[lines[1 + i][j] == '#' for j in range(w)] for i in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[i][j] = cnt == 2 or cnt == 3
                else:
                    nxt[i][j] = cnt == 3
        grid = nxt
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
