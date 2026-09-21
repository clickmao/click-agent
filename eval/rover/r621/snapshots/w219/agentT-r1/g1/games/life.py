"""康威生命游戏: 计算第 k 代网格。

输入文本格式:
    第一行: H W k
    随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'
输出: 第 k 代网格, H 行, 每行 W 个字符, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    h, w, k = (int(x) for x in lines[i].split())
    rows = [lines[i + 1 + t] for t in range(h)]

    grid = [[False] * w for _ in range(h)]
    for r in range(h):
        row = rows[r]
        for c in range(w):
            if row[c] == "#":
                grid[r][c] = True

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

    return "\n".join(
        "".join("#" if grid[r][c] else "." for c in range(w)) for r in range(h)
    )
