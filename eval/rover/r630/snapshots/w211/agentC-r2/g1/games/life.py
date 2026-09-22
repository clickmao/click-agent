"""康威生命游戏: 求第 k 代网格。

输入文本格式:
    第一行: H W k
    随后 H 行: 每行 W 个字符, 只含 '.'(死) 与 '#'(活)

solve(text) 返回: 第 k 代之后 (k=0 即初始) 的网格, H 行, 每行 W 个字符,
只含 '.' 与 '#', 末尾不带换行。
"""


_ALIVE = '#'
_DEAD = '.'


def _step(grid, h, w):
    """按 8 邻域同时更新一代; 网格外一律视为死格。"""
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            live = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == _ALIVE:
                        live += 1
            if grid[r][c] == _ALIVE:
                row.append(_ALIVE if live in (2, 3) else _DEAD)
            else:
                row.append(_ALIVE if live == 3 else _DEAD)
        out.append(''.join(row))
    return out


def solve(text):
    # 兼容任意空白: 用 splitlines 取行, 用 split 取首行数字
    lines = text.splitlines()
    tokens = lines[0].split()
    h = int(tokens[0])
    w = int(tokens[1])
    k = int(tokens[2])
    grid = []
    r = 1
    while len(grid) < h and r < len(lines):
        line = lines[r]
        if line != '':
            grid.append(line[:w])
        r += 1
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
