"""Conway 生命游戏：H 代演化。

输入（solve 的 text 参数）：
  第一行三个整数 H W k；随后 H 行，每行 W 个字符，只含 '.'（死）与 '#'（活）。
输出：第 k 代之后的网格，H 行，每行 W 个字符，末尾不带换行。
"""


def _step(grid, h, w):
    new = [['.'] * w for _ in range(h)]
    for i in range(h):
        for j in range(w):
            cnt = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == '#':
                        cnt += 1
            alive = grid[i][j] == '#'
            if alive and (cnt == 2 or cnt == 3):
                new[i][j] = '#'
            elif (not alive) and cnt == 3:
                new[i][j] = '#'
    return new


def solve(text):
    lines = text.split('\n')
    p = 0
    while p < len(lines) and lines[p].strip() == '':
        p += 1
    h, w, k = map(int, lines[p].split())
    p += 1
    grid = []
    while len(grid) < h:
        if p >= len(lines):
            break
        row = lines[p].rstrip('\r')
        p += 1
        if row == '':
            continue
        grid.append(list((row + '.' * w)[:w]))
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(r) for r in grid)
