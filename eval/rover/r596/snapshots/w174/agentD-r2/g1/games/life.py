"""康威生命游戏: 演化 k 代。

solve(text) 读入: 第一行 H W k; 随后 H 行, 每行 W 个 '.'/'#' 字符。
输出第 k 代网格, H 行, 每行 W 个字符, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                live = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            live += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if live in (2, 3) else '.'
                else:
                    new[r][c] = '#' if live == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
