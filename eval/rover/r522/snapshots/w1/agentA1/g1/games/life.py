"""康威生命游戏 H 代演化。

入参 text: 第一行 "H W k"; 随后 H 行, 每行 W 个 '.'/'#'。
返回: 第 k 代网格文本 (H 行, 行间 '\n', 末尾不带换行)。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

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
                if alive and cnt in (2, 3):
                    nxt[r][c] = "#"
                elif not alive and cnt == 3:
                    nxt[r][c] = "#"
        grid = nxt

    return "\n".join("".join(row) for row in grid)
