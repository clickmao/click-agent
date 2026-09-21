"""康威生命游戏：H 行 W 列网格演化 k 代。

入参 text: 第一行 "H W k"，随后 H 行每行 W 个 '.' 或 '#'。
返回: 第 k 代网格，H 行，末尾不带换行。
约定: 网格外一律视为死格；每代按 8 邻域同步更新。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r][:w]) for r in range(h)]

    def step(g):
        ng = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == "#":
                            n += 1
                if g[r][c] == "#":
                    ng[r][c] = "#" if n in (2, 3) else "."
                else:
                    ng[r][c] = "#" if n == 3 else "."
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
