"""康威生命游戏 (Conway's Game of Life) H 代演化。

输入格式:
    第一行: H W k   (1<=H,W<=20, 0<=k<=20)
    随后 H 行, 每行 W 个字符, 只含 '.' (死) 与 '#' (活)

规则:
    每代同时按 8 邻域更新; 网格外一律视为死格。
    活细胞邻居数为 2 或 3 -> 存活, 否则死亡。
    死细胞邻居数恰为 3 -> 复活。

输出: 第 k 代之后的网格, H 行, 每行 W 个字符 ('.' 与 '#'), 末尾不带换行。
"""


def _step(grid, h, w):
    """演进一代; 返回新的网格 (同时更新)。"""
    new = [["."] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                        n += 1
            if grid[r][c] == "#":
                new[r][c] = "#" if n in (2, 3) else "."
            else:
                new[r][c] = "#" if n == 3 else "."
    return new


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join(row) for row in grid)
