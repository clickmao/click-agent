"""康威生命游戏：H 代演化。"""


def solve(text: str) -> str:
    """返回第 k 代之后的网格。"""
    lines = text.splitlines()
    h, w, k = (int(v) for v in lines[0].split())
    grid = [list(lines[1 + i].strip()) for i in range(h)]

    def step(g):
        out = [[None] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            n += 1
                if g[r][c] == '#':
                    out[r][c] = '#' if n in (2, 3) else '.'
                else:
                    out[r][c] = '#' if n == 3 else '.'
        return out

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
