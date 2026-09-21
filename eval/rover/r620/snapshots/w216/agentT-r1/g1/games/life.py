"""康威生命游戏 H 代演化。

输入格式:
    第一行三个整数 H W k (1<=H,W<=20, 0<=k<=20)
    随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)

规则: 每代同时按 8 邻域更新, 网格外一律视为死格;
活细胞邻居数为 2 或 3 时存活, 否则死亡; 死细胞邻居数恰为 3 时复活。

输出: 第 k 代之后的网格, H 行, 每行 W 个字符, 只含 '.' 与 '#'。
"""


DEAD = "."
ALIVE = "#"


def _step(grid, h, w):
    """返回 grid 同步演化一代后的新网格(列表的列表)。"""
    new = [[DEAD] * w for _ in range(h)]
    for r in range(h):
        row = grid[r]
        for c in range(w):
            # 统计 8 邻域内的活细胞数, 越界视为死格
            n = 0
            for dr in (-1, 0, 1):
                nr = r + dr
                if nr < 0 or nr >= h:
                    continue
                nrow = grid[nr]
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nc = c + dc
                    if nc < 0 or nc >= w:
                        continue
                    if nrow[nc] == ALIVE:
                        n += 1
            if row[c] == ALIVE:
                new[r][c] = ALIVE if (n == 2 or n == 3) else DEAD
            else:
                new[r][c] = ALIVE if n == 3 else DEAD
    return new


def solve(text: str) -> str:
    """入参=完整 stdin 文本, 返回=应当写出的 stdout 文本(末尾不带换行)。"""
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].rstrip("\r")[:w]) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join(row) for row in grid)
