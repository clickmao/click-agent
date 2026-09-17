"""Conway 生命游戏 (Life) 的 H 代演化。

solve(text) 内 text 为完整 stdin 文本:
  第一行: H W k  (1<=H,W<=20, 0<=k<=20)
  随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)
返回: 第 k 代之后 (k=0 即初始) 的网格文本, H 行, 每行 W 字符, 末尾不带换行。
"""


def _step(grid, h, w):
    """单代演化: 每代同时按 8 邻域更新, 网格外一律视为死格。"""
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            live = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        live += 1
            if grid[r][c] == '#':
                row.append('#' if live in (2, 3) else '.')
            else:
                row.append('#' if live == 3 else '.')
        out.append(row)
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r][:w].ljust(w, '.')) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
