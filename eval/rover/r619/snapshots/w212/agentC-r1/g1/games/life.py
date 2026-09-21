def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i].rstrip('\n')) for i in range(h)]

    def step(g):
        ng = []
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
                if g[r][c] == '#':
                    row.append('#' if n == 2 or n == 3 else '.')
                else:
                    row.append('#' if n == 3 else '.')
            ng.append(row)
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
