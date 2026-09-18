def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    h, w, k = map(int, lines[i].split())
    i += 1
    rows = []
    while len(rows) < h:
        if i >= len(lines):
            rows.append('.' * w)
            continue
        line = lines[i].strip()
        i += 1
        if line == '':
            continue
        rows.append((line + '.' * w)[:w])
    grid = [[c == '#' for c in row] for row in rows]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                ng[y][x] = (grid[y][x] and cnt in (2, 3)) or ((not grid[y][x]) and cnt == 3)
        grid = ng
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
