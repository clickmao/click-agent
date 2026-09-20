def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    nxt[r][c] = n in (2, 3)
                else:
                    nxt[r][c] = n == 3
        grid = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
