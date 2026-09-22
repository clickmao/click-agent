"""Conway's Game of Life: H 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = [int(x) for x in lines[0].split()]
    grid = [[c == '#' for c in lines[1 + r]] for r in range(h)]

    def step(g):
        new = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                            n += 1
                new[r][c] = n == 3 or (g[r][c] and n == 2)
        return new

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
