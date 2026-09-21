"""Conway's Game of Life: H rows, W cols, k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    def step(g):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and g[nr][nc] == '#':
                            n += 1
                if g[r][c] == '#':
                    ng[r][c] = '#' if n in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if n == 3 else '.'
        return ng

    for _ in range(k):
        grid = step(grid)

    return '\n'.join(''.join(row) for row in grid)
