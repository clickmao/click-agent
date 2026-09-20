def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            n += 1
                if grid[y][x]:
                    nxt[y][x] = n in (2, 3)
                else:
                    nxt[y][x] = n == 3
        grid = nxt

    out = []
    for y in range(h):
        out.append(''.join('#' if grid[y][x] else '.' for x in range(w)))
    return '\n'.join(out)
