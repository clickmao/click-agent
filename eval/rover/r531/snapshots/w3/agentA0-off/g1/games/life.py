"""Conway 生命游戏: H 代演化。"""


def _step(grid, h, w):
    """单代演化（同时更新）; 网格外视为死格。"""
    nd = [[0] * w for _ in range(h)]
    for r in range(h):
        row = grid[r]
        for c in range(w):
            if row[c] != '#':
                continue
            for dr in (-1, 0, 1):
                nr = r + dr
                if 0 <= nr < h:
                    nrow = grid[nr]
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nc = c + dc
                        if 0 <= nc < w:
                            nd[nr][nc] += 1
    out = []
    for r in range(h):
        line = []
        for c in range(w):
            alive = grid[r][c] == '#'
            n = nd[r][c]
            if alive:
                line.append('#' if (n == 2 or n == 3) else '.')
            else:
                line.append('#' if n == 3 else '.')
        out.append(''.join(line))
    return out


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip() if idx < len(lines) else ''
        idx += 1
        grid.append(list(row.ljust(w, '.')[:w]))
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
