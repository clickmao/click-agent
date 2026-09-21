"""康威生命游戏: H 行 W 列网格演化 k 代（网格外视为死格）。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[ch == '#' for ch in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                nxt[r][c] = (grid[r][c] and n in (2, 3)) or (not grid[r][c] and n == 3)
        grid = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
