"""康威生命游戏 H 代演化。

读入第一行三个整数 H W k, 随后 H 行每行 W 个字符('.', '#')。
输出第 k 代之后的网格。
"""


def _parse(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split()[:3])
    grid = [list(lines[1 + r][:w].ljust(w, '.')) for r in range(h)]
    return h, w, k, grid


def _step(grid, h, w):
    new = [['.'] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            alive = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                        alive += 1
            if grid[r][c] == '#':
                new[r][c] = '#' if alive in (2, 3) else '.'
            else:
                new[r][c] = '#' if alive == 3 else '.'
    return new


def solve(text):
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
