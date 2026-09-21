def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [lines[1 + i] for i in range(h)]

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
                if alive:
                    row.append('#' if n in (2, 3) else '.')
                else:
                    row.append('#' if n == 3 else '.')
            out.append(''.join(row))
        return out

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(grid)
