"""康威生命游戏: 对初始网格演化 k 代后输出。

输入文本 (stdin 全部):
    第一行: H W k   (1<=H,W<=20, 0<=k<=20)
    随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'。

规则: 每代同时更新; 网格外一律视为死格;
      活细胞邻居数 2 或 3 -> 存活, 否则死亡;
      死细胞邻居数恰为 3 -> 复活。
输出: 第 k 代之后 (k=0 即初始) 的网格, H 行, 每行 W 个字符, 末尾不带换行。
"""


def _step(grid, h, w):
    """单代演化 (同时更新)。grid 为字符列表的列表。"""
    nxt = [['.'] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            if alive:
                nxt[r][c] = '#' if n in (2, 3) else '.'
            else:
                nxt[r][c] = '#' if n == 3 else '.'
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r][:w].ljust(w, '.')) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
