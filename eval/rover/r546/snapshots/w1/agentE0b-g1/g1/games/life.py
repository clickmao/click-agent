def solve(text):
    lines = text.splitlines()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + i]] for i in range(h)]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and g[nr][nc]:
                    cnt += 1
        return cnt

    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c]:
                    ng[r][c] = 1 if n == 2 or n == 3 else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
