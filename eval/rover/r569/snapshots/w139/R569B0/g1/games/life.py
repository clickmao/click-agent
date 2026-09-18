"""康威生命游戏：H 代演化。

读入: 第一行三个整数 H W k; 随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)。
输出: 第 k 代之后的网格, H 行, 每行 W 个字符。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])

    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ""
        row = row[:w].ljust(w, ".")
        grid.append(row)

    for _ in range(k):
        new = []
        for r in range(h):
            out = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                alive = grid[r][c] == "#"
                if alive:
                    out.append("#" if cnt == 2 or cnt == 3 else ".")
                else:
                    out.append("#" if cnt == 3 else ".")
            new.append("".join(out))
        grid = new

    return "\n".join(grid)
