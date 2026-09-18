"""康威生命游戏: k 代同时演化。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ''
        row = row.ljust(w, '.')[:w]
        grid.append([c == '#' for c in row])
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
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
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
