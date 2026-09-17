def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(H):
        row = lines[idx + 1 + r] if idx + 1 + r < len(lines) else ''
        row = row.rstrip('\r')
        row = (row + '.' * W)[:W]
        grid.append(list(row))

    def step(g):
        ng = [['.'] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < H and 0 <= nj < W and g[ni][nj] == '#':
                            n += 1
                if g[i][j] == '#':
                    ng[i][j] = '#' if n in (2, 3) else '.'
                else:
                    ng[i][j] = '#' if n == 3 else '.'
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
