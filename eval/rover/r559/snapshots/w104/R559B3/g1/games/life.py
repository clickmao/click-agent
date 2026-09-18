def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in lines[1 + r]] for r in range(h)]

    def neighbors(g, r, c):
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr = r + dr
                nc = c + dc
                if 0 <= nr < h and 0 <= nc < w and g[nr][nc]:
                    cnt += 1
        return cnt

    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbors(grid, r, c)
                if grid[r][c]:
                    ng[r][c] = 1 if n in (2, 3) else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        grid = ng

    return '\n'.join(''.join('#' if grid[r][c] else '.' for c in range(w)) for r in range(h))
