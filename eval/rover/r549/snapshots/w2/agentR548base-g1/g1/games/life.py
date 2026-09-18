def solve(text: str) -> str:
    lines = text.strip('\n').split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [[c == '#' for c in lines[1 + i].strip()] for i in range(H)]
    for _ in range(k):
        new = [[False] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < H and 0 <= nj < W and grid[ni][nj]:
                            cnt += 1
                if grid[i][j]:
                    new[i][j] = cnt == 2 or cnt == 3
                else:
                    new[i][j] = cnt == 3
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
