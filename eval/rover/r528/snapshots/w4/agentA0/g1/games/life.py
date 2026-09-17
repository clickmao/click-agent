"""康威生命游戏: 在 H x W 网格上演化 k 代。

规则: 每代同时更新, 8 邻域, 网格外视为死格。
    活细胞邻居数 2 或 3 -> 存活; 否则死亡。
    死细胞邻居数恰为 3 -> 复活。
"""


def _step(grid, H, W):
    """单代演化, 返回新网格(同时更新)。"""
    new = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        new.append(''.join(row))
    return new


def solve(text: str) -> str:
    lines = text.splitlines()
    H, W, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i][:W] for i in range(H)]
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
