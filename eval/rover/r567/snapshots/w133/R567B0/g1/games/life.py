"""康威生命游戏（Conway's Game of Life）：H 代同时演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]

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
                if grid[r][c]:
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
