"""life: 康威生命游戏 H 代演化。

输入格式：
    第一行 H W k
    随后 H 行，每行 W 个字符（'.' 死 / '#' 活）
输出：第 k 代网格，H 行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i][:w].ljust(w, ".")) for i in range(h)]

    def step(g):
        ng = [["."] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and g[ni][nj] == "#":
                            cnt += 1
                if g[i][j] == "#":
                    ng[i][j] = "#" if cnt in (2, 3) else "."
                else:
                    ng[i][j] = "#" if cnt == 3 else "."
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
