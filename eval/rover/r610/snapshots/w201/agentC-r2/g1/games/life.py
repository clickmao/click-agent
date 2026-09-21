def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r][:w]] for r in range(h)]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                    cnt += 1
        return cnt

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c]:
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
