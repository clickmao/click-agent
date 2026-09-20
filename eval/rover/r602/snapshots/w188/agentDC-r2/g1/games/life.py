"""康威生命游戏: 输出第 k 代之后的网格。

读入: 第一行三个整数 H W k; 随后 H 行, 每行 W 个字符 ('.' 死 / '#' 活)。
规则: 每代同时按 8 邻域更新, 网格外一律视为死格;
      活细胞邻居数 2 或 3 时存活, 否则死亡; 死细胞邻居数恰 3 时复活。
输出: 第 k 代之后 (k=0 即初始) 的网格, H 行, 每行 W 个字符。
"""

ALIVE = '#'
DEAD = '.'


def _step(grid, h, w):
    """返回下一代网格 (list[list[bool]])。网格外视为死格。"""
    nxt = [[False] * w for _ in range(h)]
    for r in range(h):
        row = grid[r]
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                rr = r + dr
                if rr < 0 or rr >= h:
                    continue
                nrow = grid[rr]
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    cc = c + dc
                    if 0 <= cc < w and nrow[cc]:
                        n += 1
            if row[c]:
                nxt[r][c] = (n == 2 or n == 3)
            else:
                nxt[r][c] = (n == 3)
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split()[:3])
    grid = []
    for i in range(h):
        row_src = lines[1 + i] if 1 + i < len(lines) else ''
        row = [ch == ALIVE for ch in row_src[:w]]
        while len(row) < w:
            row.append(False)
        grid.append(row)

    for _ in range(k):
        grid = _step(grid, h, w)

    return '\n'.join(''.join(ALIVE if cell else DEAD for cell in row) for row in grid)
