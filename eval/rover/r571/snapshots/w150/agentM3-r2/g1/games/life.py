def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i]
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    new[y][x] = cnt == 2 or cnt == 3
                else:
                    new[y][x] = cnt == 3
        grid = new

    out = []
    for y in range(h):
        out.append(''.join('#' if grid[y][x] else '.' for x in range(w)))
    return '\n'.join(out)
