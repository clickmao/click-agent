def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r]
        cells = [1 if c == '#' else 0 for c in row.strip()]
        while len(cells) < w:
            cells.append(0)
        grid.append(cells[:w])
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
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
                    new[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    new[y][x] = 1 if cnt == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
