def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    def step(g):
        ng = []
        for y in range(h):
            row = []
            for x in range(w):
                c = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == '#':
                            c += 1
                if g[y][x] == '#':
                    row.append('#' if c in (2, 3) else '.')
                else:
                    row.append('#' if c == 3 else '.')
            ng.append(row)
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(r) for r in grid)
