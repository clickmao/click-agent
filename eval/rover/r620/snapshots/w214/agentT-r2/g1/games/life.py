"""康威生命游戏：H 代演化（第 k 代输出）。

读入: 第一行三个整数 H W k; 随后 H 行，每行 W 个字符，只含 '.' 与 '#'。
规则: 每代同时按 8 邻域更新，网格外视为死格。
输出: 第 k 代之后的网格，H 行、每行 W 个字符。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split()[:3])
    idx += 1

    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ""
        row = row.replace("\r", "")
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append([c == "#" for c in row[:w]])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
