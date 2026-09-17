"""康威生命游戏 H 代演化。"""


def _step(grid, h, w):
    """同时（同步）演化一代；网格外一律视为死格。"""
    nxt = []
    for r in range(h):
        row = []
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if (n == 2 or n == 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        nxt.append(row)
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i].rstrip('\r')
        row = (row + '.' * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
