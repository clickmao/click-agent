"""Conway 生命游戏 H 代演化.

stdin: 第一行 H W k; 随后 H 行, 每行 W 个 '.'/'#'.
stdout: 第 k 代(含 k=0 初始)后的网格, H 行.
"""


def _parse(text):
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    return h, w, k, grid


def _step(h, w, grid):
    """同时按 8 邻域更新一代; 网格外视为死格."""
    nxt = [["."] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        n += 1
            alive = grid[r][c] == "#"
            # 活细胞邻居 2/3 存活; 死细胞邻居恰为 3 复活
            if alive:
                nxt[r][c] = "#" if (n == 2 or n == 3) else "."
            else:
                nxt[r][c] = "#" if n == 3 else "."
    return nxt


def solve(text):
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(h, w, grid)
    return "\n".join("".join(row) for row in grid)
