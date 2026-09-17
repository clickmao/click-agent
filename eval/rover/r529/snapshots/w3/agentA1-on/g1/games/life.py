"""康威生命游戏: 演化 k 代后输出网格。

输入: 首行 H W k; 随后 H 行, 每行 W 个字符 ('.' 死 / '#' 活)。
规则: 每代同时按 8 邻域更新, 网格外视为死格。
输出: k 代后网格 (k=0 为初始), H 行 W 列, 无末尾换行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        grid.append(list(lines[idx].rstrip("\r")))
        idx += 1

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                alive = grid[r][c] == "#"
                if alive and (cnt == 2 or cnt == 3):
                    nxt[r][c] = "#"
                elif not alive and cnt == 3:
                    nxt[r][c] = "#"
        grid = nxt

    return "\n".join("".join(row) for row in grid)
