"""康威生命游戏：H 代演化。

solve(text) 读入首行 "H W k"，随后 H 行每行 W 个字符（'.' 死 / '#' 活），
返回第 k 代之后（k=0 即初始）的网格文本（H 行，末尾不带换行）。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ""
        cells = [(c == "#") for c in row[:w]]
        while len(cells) < w:
            cells.append(False)
        grid.append(cells)

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

    out = []
    for r in range(h):
        out.append("".join("#" if grid[r][c] else "." for c in range(w)))
    return "\n".join(out)
