"""康威生命游戏 (Conway's Game of Life) H 代演化。

输入格式 (完整 stdin 文本):
    第一行三个整数 H W k  (1<=H,W<=20, 0<=k<=20)
    随后 H 行, 每行 W 个字符, 只含 '.' (死) 与 '#' (活)

规则: 每代同时按 8 邻域更新, 网格外一律视为死格。
    - 活细胞邻居数 2 或 3 -> 存活, 否则死亡
    - 死细胞邻居数恰为 3   -> 复活

输出: 第 k 代之后的网格 (k=0 即初始), H 行, 每行 W 个字符, 末尾不带换行。
"""

from typing import List


def _step(grid: List[List[int]], h: int, w: int) -> List[List[int]]:
    """按 8 邻域同步更新一代, 返回新网格 (0=死, 1=活)。"""
    nxt = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                        n += 1
            alive = grid[r][c] == 1
            nxt[r][c] = 1 if (n == 3 or (alive and n == 2)) else 0
    return nxt


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (末尾不带换行)。"""
    lines = text.split("\n")
    # 去除可能存在的末尾空行造成的干扰, 但保留前导结构
    if lines and lines[-1] == "":
        lines = lines[:-1]

    h, w, k = (int(x) for x in lines[0].split())
    grid = [[1 if ch == "#" else 0 for ch in lines[1 + r][:w]] for r in range(h)]

    for _ in range(k):
        grid = _step(grid, h, w)

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
