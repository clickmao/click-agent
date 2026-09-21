"""康威生命游戏：H 代演化后输出网格。"""


def _step(grid):
    h = len(grid)
    w = len(grid[0])
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
                row.append('#' if (cnt == 2 or cnt == 3) else '.')
            else:
                row.append('#' if cnt == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i].strip() for i in range(h)]
    for _ in range(k):
        grid = _step(grid)
    return '\n'.join(grid)
