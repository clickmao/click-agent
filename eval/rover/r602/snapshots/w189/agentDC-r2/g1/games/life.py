"""康威生命游戏：给定网格演化 k 代。

solve(text) 入参为完整 stdin 文本，返回应当写出的 stdout 文本（末尾无换行）。

输入格式：
    第一行: H W k   (1<=H,W<=20, 0<=k<=20)
    随后 H 行: 每行 W 个字符，'.' 为死，'#' 为活
输出格式：
    演化 k 代后的网格，H 行，每行 W 个字符，仅 '.' 与 '#'
规则：
    每代同时按 8 邻域更新，网格外一律视为死格。
    活细胞邻居数 2 或 3 时存活，否则死亡；死细胞邻居数恰为 3 时复活。
"""
from typing import List


def _step(grid: List[List[bool]], h: int, w: int) -> List[List[bool]]:
    nxt = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            live = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        live += 1
            if grid[r][c]:
                nxt[r][c] = live == 2 or live == 3
            else:
                nxt[r][c] = live == 3
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = [[False] * w for _ in range(h)]
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ""
        row = row.rstrip("\r")
        for c in range(w):
            grid[r][c] = c < len(row) and row[c] == "#"
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
