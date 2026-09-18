def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                nb = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            nb += 1
                if grid[i][j] == '#':
                    nxt[i][j] = '#' if nb in (2, 3) else '.'
                else:
                    nxt[i][j] = '#' if nb == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
