def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[False] * w for _ in range(h)]
    for i in range(h):
        row = lines[1 + i]
        for j in range(w):
            grid[i][j] = (j < len(row) and row[j] == '#')
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
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
                    ng[i][j] = cnt in (2, 3)
                else:
                    ng[i][j] = cnt == 3
        grid = ng
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
