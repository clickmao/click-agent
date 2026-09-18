def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]

    def step(g):
        out = []
        for r in range(h):
            row = []
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            n += 1
                alive = g[r][c] == '#'
                row.append('#' if (n == 3 or (alive and n == 2)) else '.')
            out.append(row)
        return out

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
