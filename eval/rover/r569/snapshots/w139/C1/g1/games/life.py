def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        grid.append(list(lines[idx].rstrip("\n")))
        idx += 1
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                            cnt += 1
                if grid[i][j] == '#':
                    new[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    new[i][j] = '#' if cnt == 3 else '.'
        grid = new
    return "\n".join("".join(row) for row in grid)
