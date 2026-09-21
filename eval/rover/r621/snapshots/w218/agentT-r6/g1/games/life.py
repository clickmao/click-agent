"""康威生命游戏的 H 代演化。

输入首行: H W k (1<=H,W<=20, 0<=k<=20)
随后 H 行, 每行 W 个字符, 只含 '.' 与 '#'。
输出: 第 k 代之后的网格, H 行, 每行 W 个字符, 末尾不带换行。
"""


def _step(grid, h, w):
    nxt = []
    for r in range(h):
        row = []
        for c in range(w):
            cnt = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        cnt += 1
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if cnt == 2 or cnt == 3 else '.')
            else:
                row.append('#' if cnt == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    first = [tok for tok in lines[0].split()]
    if len(first) < 3:
        for line in lines[1:]:
            first.extend(line.split())
            if len(first) >= 3:
                break
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    body = []
    for line in lines[1:]:
        s = line.rstrip('\r')
        if s == '':
            continue
        body.append(s)
    grid = body[:h]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
