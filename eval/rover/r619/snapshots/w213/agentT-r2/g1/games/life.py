def solve(text):
    data = text.split()
    if not data:
        return ""
    idx = 0
    H = int(data[idx]); idx += 1
    W = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    grid = []
    for _ in range(H):
        grid.append(list(data[idx])); idx += 1
    for _ in range(k):
        ng = [["."] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < H and 0 <= nj < W and grid[ni][nj] == "#":
                            cnt += 1
                if grid[i][j] == "#":
                    ng[i][j] = "#" if cnt == 2 or cnt == 3 else "."
                else:
                    ng[i][j] = "#" if cnt == 3 else "."
        grid = ng
    return "\n".join("".join(row) for row in grid)
