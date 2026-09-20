def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        grid.append([c == '#' for c in lines[idx + i][:w]])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        yy = y + dy
                        xx = x + dx
                        if 0 <= yy < h and 0 <= xx < w and grid[yy][xx]:
                            n += 1
                if grid[y][x]:
                    nxt[y][x] = n == 2 or n == 3
                else:
                    nxt[y][x] = n == 3
        grid = nxt
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
