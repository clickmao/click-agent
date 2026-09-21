def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(h):
        row = lines[idx + 1 + r]
        grid.append([1 if c == '#' else 0 for c in row[:w]])

    def step(g):
        ng = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and g[ni][nj]:
                            cnt += 1
                if g[i][j]:
                    ng[i][j] = 1 if cnt in (2, 3) else 0
                else:
                    ng[i][j] = 1 if cnt == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
