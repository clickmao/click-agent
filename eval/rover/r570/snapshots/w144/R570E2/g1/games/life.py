"""Conway's Game of Life: evolve HxW grid k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    rows = lines[1:1 + h]
    grid = [[1 if c == '#' else 0 for c in row] for row in rows]
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w:
                            cnt += grid[ni][nj]
                if grid[i][j]:
                    new[i][j] = 1 if cnt in (2, 3) else 0
                else:
                    new[i][j] = 1 if cnt == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
