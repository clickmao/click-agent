"""康威生命游戏：k 代演化。

输入格式（第一行）：H W k
随后 H 行、每行 W 个字符，'.' 表示死，'#' 表示活。
输出：第 k 代之后的网格（k=0 即初始），H 行、每行 W 个字符。
solve 返回的字符串末尾不带换行。
"""


def _step(grid, H, W):
    nxt = []
    for i in range(H):
        row = []
        for j in range(W):
            n = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < H and 0 <= nj < W and grid[ni][nj] == '#':
                        n += 1
            if grid[i][j] == '#':
                row.append('#' if (n == 2 or n == 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text):
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = list(lines[1:1 + H])
    for _ in range(k):
        grid = _step(grid, H, W)
    return '\n'.join(grid)
