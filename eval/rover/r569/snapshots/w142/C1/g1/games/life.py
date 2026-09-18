def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(line[:W]) for line in lines[1:1 + H]]

    for _ in range(k):
        nxt = [['.'] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < H and 0 <= nj < W and grid[ni][nj] == '#':
                            cnt += 1
                if grid[i][j] == '#':
                    nxt[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    nxt[i][j] = '#' if cnt == 3 else '.'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
