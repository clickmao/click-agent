"""康威生命游戏: 读入 H W k 与 H 行 W 列网格, 返回第 k 代网格文本。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1].strip() == '':
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[False] * w for _ in range(h)]
    for i in range(h):
        row = lines[1 + i]
        for j in range(w):
            grid[i][j] = (row[j] == '#')

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                n = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            n += 1
                if grid[i][j]:
                    nxt[i][j] = (n == 2 or n == 3)
                else:
                    nxt[i][j] = (n == 3)
        grid = nxt

    out = []
    for i in range(h):
        out.append(''.join('#' if grid[i][j] else '.' for j in range(w)))
    return '\n'.join(out)
