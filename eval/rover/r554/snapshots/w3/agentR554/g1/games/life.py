def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[c == '#' for c in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            n += 1
                if grid[i][j]:
                    new[i][j] = n in (2, 3)
                else:
                    new[i][j] = n == 3
        grid = new
    return '\n'.join(''.join('#' if grid[i][j] else '.' for j in range(w)) for i in range(h))
