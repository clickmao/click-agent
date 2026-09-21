"""康威生命游戏：H 代（同时更新，8 邻域，界外视为死格）。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]

    def alive(r, c):
        if r < 0 or r >= h or c < 0 or c >= w:
            return 0
        return 1 if grid[r][c] == '#' else 0

    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        n += alive(r + dr, c + dc)
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if n in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
