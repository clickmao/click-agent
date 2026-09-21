"""康威生命游戏: 演化 k 代后输出网格。

solve(text) 读入:
  第一行 H W k
  随后 H 行, 每行 W 个字符, 只含 '.'(死) 与 '#'(活)
返回: 第 k 代之后的网格, H 行, 每行 W 个字符, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx]
        idx += 1
        grid.append([1 if c == '#' else 0 for c in row[:w]])

    def step(g):
        nxt = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w:
                            cnt += g[ni][nj]
                if g[i][j] == 1:
                    nxt[i][j] = 1 if cnt == 2 or cnt == 3 else 0
                else:
                    nxt[i][j] = 1 if cnt == 3 else 0
        return nxt

    for _ in range(k):
        grid = step(grid)

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
