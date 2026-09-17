"""康威生命游戏 (Conway's Game of Life) 的 k 代演化。

规格:
  第一行: H W k  (1<=H,W<=20, 0<=k<=20)
  随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)。
  每代同时按 8 邻域更新, 网格外一律视为死格。
  活细胞邻居数为 2 或 3 时存活, 否则死亡; 死细胞邻居数恰为 3 时复活。
输出: 第 k 代之后的网格 (k=0 即初始), H 行, 每行 W 字符, 末尾不带换行。
"""


def _step(grid, h, w):
    """按 8 邻域同时演化一代, 边界外视为死格。"""
    out = [['.'] * w for _ in range(h)]
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
                out[r][c] = '#' if (alive == 2 or alive == 3) else '.'
            else:
                out[r][c] = '#' if alive == 3 else '.'
    return out


def solve(text: str) -> str:
    """纯函数: stdin 文本 -> stdout 文本 (不带末尾换行)。"""
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].rstrip('\r')) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
