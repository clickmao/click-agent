"""康威生命游戏: 输出第 k 代之后的网格。

输入首行: H W k
随后 H 行、每行 W 个字符 ('.' 死 / '#' 活)。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(v) for v in lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ''
        row = row.rstrip('\r')
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                alive = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            alive += 1
                if grid[y][x]:
                    nxt[y][x] = alive == 2 or alive == 3
                else:
                    nxt[y][x] = alive == 3
        grid = nxt

    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
