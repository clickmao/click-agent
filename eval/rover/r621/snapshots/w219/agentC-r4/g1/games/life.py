"""康威生命游戏：输入网格与前进步数 k，输出第 k 代网格。"""


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
            if grid[r][c] == '#':
                row.append('#' if cnt == 2 or cnt == 3 else '.')
            else:
                row.append('#' if cnt == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i].strip() for i in range(h)]
    for _ in range(k):
        grid = _step(grid)
    return '\n'.join(grid)
