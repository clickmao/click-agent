"""康威生命游戏：H 代演化。

读入: 第一行 H W k; 随后 H 行 W 个字符 ('.'/'#')。
输出: 第 k 代网格 (k=0 为初始), 末尾不带换行。
"""


def _step(grid, h, w):
    """执行一代演化, 返回新网格 (list[list[str]])。网格外视为死格。"""
    new = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            # 统计 8 邻域活细胞数
            cnt = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                        cnt += 1
            if grid[r][c]:
                new[r][c] = cnt == 2 or cnt == 3
            else:
                new[r][c] = cnt == 3
    return new


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[ch == '#' for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
