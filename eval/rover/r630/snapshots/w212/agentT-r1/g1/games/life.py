"""康威生命游戏：H 代演化。

输入格式：第一行 ``H W k``（H,W 属于 1..20，k 属于 0..20），随后 H 行、每行 W 个
字符，只含 '.'（死）与 '#'（活）。
规则：每代同时按 8 邻域更新，网格外一律视为死格；活细胞邻居数为 2 或 3 时存活，
否则死亡；死细胞邻居数恰为 3 时复活。
输出：第 k 代之后（k=0 即初始）的网格，H 行、每行 W 个字符。
"""


def _step(grid, h, w):
    """返回同时更新一代后的网格（list of list of bool）。"""
    new = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        n += 1
            if grid[r][c]:
                new[r][c] = (n == 2 or n == 3)
            else:
                new[r][c] = (n == 3)
    return new


def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([ch == '#' for ch in row[:w]])
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
