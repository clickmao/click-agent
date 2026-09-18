"""康威生命游戏 (Conway's Game of Life) H 代演化。

solve(text) 读入:
  第一行三个整数 H W k
  随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)
输出: 第 k 代后的网格 (k=0 即初始)。
"""


def _step(grid, H, W):
    """按 8 邻域同时更新一代, 网格外视为死格。"""
    new = []
    for r in range(H):
        row = []
        for c in range(W):
            cnt = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == '#':
                        cnt += 1
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if cnt in (2, 3) else '.')
            else:
                row.append('#' if cnt == 3 else '.')
        new.append(''.join(row))
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i][:W] for i in range(H)]
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
