"""康威生命游戏：读入 H W k 与初始网格，输出第 k 代网格。

约定：solve 返回的字符串末尾不带换行。
"""


def solve(text: str) -> str:
    """text = 完整 stdin 文本；返回第 k 代网格（H 行，每行 W 个字符）。"""
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
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
                if grid[r][c] == "#":
                    nxt[r][c] = "#" if n == 2 or n == 3 else "."
                else:
                    nxt[r][c] = "#" if n == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
