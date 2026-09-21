"""康威生命游戏 H 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in lines[i + 1][:w]] for i in range(h)]

    def step(g):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += g[rr][cc]
                if g[r][c] == 1:
                    ng[r][c] = 1 if n in (2, 3) else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
