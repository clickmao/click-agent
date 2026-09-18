"""康威生命游戏: k 代演化。

读入: 第一行 H W k; 随后 H 行, 每行 W 个字符 '.'/'#'。
输出: 第 k 代之后的网格, H 行 W 列。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if n in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
