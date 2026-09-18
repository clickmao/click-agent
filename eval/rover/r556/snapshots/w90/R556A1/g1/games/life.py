"""Conway's Game of Life: k generations on an H x W grid."""


def _step(grid, h, w):
    new = [[0] * w for _ in range(h)]
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
                new[r][c] = 1 if cnt in (2, 3) else 0
            else:
                new[r][c] = 1 if cnt == 3 else 0
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r].strip()] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
