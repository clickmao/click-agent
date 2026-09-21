"""康威生命游戏 H 代演化。

读入: 第一行三个整数 H W k (H,W in 1..20, k in 0..20); 随后 H 行 W 个字符 (. 或 #)。
输出: 第 k 代之后的网格, H 行每行 W 个字符, 末尾不带换行。
"""


def _step(grid, h, w):
    nxt = []
    for r in range(h):
        row = grid[r]
        out = []
        for c in range(w):
            cnt = 0
            for dr in (-1, 0, 1):
                nr = r + dr
                if nr < 0 or nr >= h:
                    continue
                nrow = grid[nr]
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nc = c + dc
                    if nc < 0 or nc >= w:
                        continue
                    if nrow[nc] == '#':
                        cnt += 1
            alive = row[c] == '#'
            if alive:
                out.append('#' if (cnt == 2 or cnt == 3) else '.')
            else:
                out.append('#' if cnt == 3 else '.')
        nxt.append(''.join(out))
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [lines[1 + i].strip() for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
