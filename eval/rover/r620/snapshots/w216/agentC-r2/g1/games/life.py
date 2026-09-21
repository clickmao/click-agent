"""Conway's Game of Life: k 代演化。

约定: text 为该游戏的完整 stdin 文本; 返回应当写出的 stdout 文本, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
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
                new[r][c] = (grid[r][c] and n in (2, 3)) or ((not grid[r][c]) and n == 3)
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
