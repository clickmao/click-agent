"""康威生命游戏: 演化 k 代后输出网格。

stdin: 首行 "H W k"; 随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'。
stdout: 第 k 代网格, H 行 W 列, 末尾不带换行。
"""


def _step(grid, h, w):
    nxt = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        n += 1
            if grid[r][c]:
                nxt[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                nxt[r][c] = 1 if n == 3 else 0
    return nxt


def solve(text):
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = []
    for r in range(h):
        row = lines[1 + r]
        grid.append([1 if ch == "#" else 0 for ch in row[:w]])
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
