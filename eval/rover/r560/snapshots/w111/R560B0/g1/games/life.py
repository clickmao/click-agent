def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i]) for i in range(h)]
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
                alive = grid[i][j] == '#'
                if alive:
                    new[i][j] = '#' if cnt in (2, 3) else '.'
                else:
                    new[i][j] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
