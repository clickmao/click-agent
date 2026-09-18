"""康威生命游戏: 同时按 8 邻域演化 k 代。"""


def _step(grid):
    """对网格做一次同步更新, 网格外一律视为死格。"""
    h = len(grid)
    w = len(grid[0])
    new = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        n += 1
            if grid[r][c]:
                new[r][c] = 1 if (n == 2 or n == 3) else 0
            else:
                new[r][c] = 1 if n == 3 else 0
    return new


def solve(text):
    lines = text.split("\n")
    first = lines[0].split()
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = [[1 if ch == "#" else 0 for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        grid = _step(grid)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
