"""康威生命游戏 H 代演化。

入参：完整 stdin 文本；返回：第 k 代网格，末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        grid.append(list(lines[1 + i]))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == "#":
                            cnt += 1
                if grid[i][j] == "#":
                    nxt[i][j] = "#" if cnt in (2, 3) else "."
                else:
                    nxt[i][j] = "#" if cnt == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
