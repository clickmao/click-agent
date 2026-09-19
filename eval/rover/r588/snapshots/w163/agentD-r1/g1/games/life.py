def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split()[:3])
    grid = [list(lines[1 + i][:w].ljust(w, '.')) for i in range(h)]
    for _ in range(k):
        nxt = []
        for y in range(h):
            row = []
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and grid[yy][xx] == '#':
                            n += 1
                alive = grid[y][x] == '#'
                row.append('#' if (n == 3 or (alive and n == 2)) else '.')
            nxt.append(row)
        grid = nxt
    return '\n'.join(''.join(r) for r in grid)
