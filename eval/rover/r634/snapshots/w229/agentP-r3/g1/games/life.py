"""康威生命游戏：第 k 代演化。

输入格式:
    第一行 H W k
    随后 H 行，每行 W 个字符，只含 '.' 与 '#'
输出格式:
    k 代之后的网格，H 行，每行 W 个字符（末尾不带换行）
"""


NEIGHBORS = ((-1, -1), (-1, 0), (-1, 1),
             (0, -1), (0, 1),
             (1, -1), (1, 0), (1, 1))


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ''
        idx += 1
        row = (row.strip() + '.' * w)[:w]
        grid.append(list(row))

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr, dc in NEIGHBORS:
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        cnt += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if cnt == 2 or cnt == 3 else '.'
                else:
                    nxt[r][c] = '#' if cnt == 3 else '.'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
