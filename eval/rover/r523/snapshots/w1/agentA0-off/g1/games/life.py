"""life: 康威生命游戏 H 代演化。

输入:
    第一行三个整数 H W k (H,W 属于 1..20, k 属于 0..20)
    随后 H 行, 每行 W 个字符, 只含 '.' (死) 与 '#' (活)

规则:
    每代同时按 8 邻域更新, 网格外一律视为死格。
    活细胞邻居数 2 或 3 -> 存活, 否则死亡; 死细胞邻居数恰为 3 -> 复活。

输出:
    第 k 代之后的网格, H 行, 每行 W 个字符, 只含 '.' 与 '#'。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1

    grid = []
    for i in range(h):
        row = lines[idx + i]
        grid.append([1 if row[j] == "#" else 0 for j in range(w)])

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            n += grid[nr][nc]
                if grid[r][c]:
                    nxt[r][c] = 1 if n in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if n == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
