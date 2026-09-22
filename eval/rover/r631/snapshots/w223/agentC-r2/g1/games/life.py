"""康威生命游戏 H 代演化。

输入格式:
    第一行三个整数 H W k (H,W 属于 1..20, k 属于 0..20)
    随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)

规则: 每代同时按 8 邻域更新, 网格外一律视为死格;
活细胞邻居数为 2 或 3 时存活, 否则死亡; 死细胞邻居数恰为 3 时复活。

输出: 第 k 代之后的网格, H 行, 每行 W 个字符, 只含 '.' 与 '#'。
"""


def solve(text: str) -> str:
    """返回第 k 代演化后的网格文本, 末尾不带换行。"""
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    for _ in range(k):
        new_grid = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nbrs = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            nbrs += 1
                if grid[r][c] == '#':
                    new_grid[r][c] = '#' if nbrs in (2, 3) else '.'
                else:
                    new_grid[r][c] = '#' if nbrs == 3 else '.'
        grid = new_grid

    return '\n'.join(''.join(row) for row in grid)
