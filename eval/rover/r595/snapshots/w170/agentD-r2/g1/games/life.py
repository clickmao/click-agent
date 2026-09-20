def _step(grid, h, w):
    ng = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            cnt = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                        cnt += 1
            if grid[r][c]:
                ng[r][c] = 1 if cnt in (2, 3) else 0
            else:
                ng[r][c] = 1 if cnt == 3 else 0
    return ng


def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
