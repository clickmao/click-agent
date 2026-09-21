"""康威生命游戏: H 代演化。

输入: 第一行 H W k; 随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'。
输出: 第 k 代之后的网格, H 行, 每行 W 个字符。
"""


def _parse(text):
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(v) for v in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        grid.append(list(lines[idx]))
        idx += 1
    return h, w, k, grid


def _step(h, w, grid):
    nxt = [["."] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        n += 1
            if grid[r][c] == "#":
                nxt[r][c] = "#" if n in (2, 3) else "."
            else:
                nxt[r][c] = "#" if n == 3 else "."
    return nxt


def solve(text):
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(h, w, grid)
    return "\n".join("".join(row) for row in grid)
