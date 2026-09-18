"""康威生命游戏 H 代演化。

stdin 首行: H W k
随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'。
输出第 k 代网格（k=0 即初始）, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = []
    for r in range(h):
        row = lines[1 + r]
        grid.append([c == "#" for c in row[:w]])
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
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
                    new[r][c] = n == 2 or n == 3
                else:
                    new[r][c] = n == 3
        grid = new
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
