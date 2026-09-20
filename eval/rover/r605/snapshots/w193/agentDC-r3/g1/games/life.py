"""康威生命游戏 H 代演化。

输入: 第一行三个整数 H W k (H,W 属于 1..20, k 属于 0..20); 随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)。
规则: 每代同时按 8 邻域更新, 网格外一律视为死格; 活细胞邻居数为 2 或 3 时存活, 否则死亡; 死细胞邻居数恰为 3 时复活。
输出: 第 k 代之后的网格, H 行, 每行 W 个字符。
"""


def solve(text: str) -> str:
    # 仅取非空行, 避免首尾空行干扰
    lines = [ln for ln in text.splitlines() if ln.strip() != '']
    idx = 0
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx].strip()
        idx += 1
        # 容错: 行长度不足时用 '.' 补齐, 超出时截断
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        new_grid = [[False] * w for _ in range(h)]
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
                    new_grid[r][c] = n in (2, 3)
                else:
                    new_grid[r][c] = (n == 3)
        grid = new_grid

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
