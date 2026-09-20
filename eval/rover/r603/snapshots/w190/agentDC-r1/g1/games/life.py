def solve(text):
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]
    for _ in range(k):
        new = []
        for y in range(H):
            row = []
            for x in range(W):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] == '#':
                            cnt += 1
                if grid[y][x] == '#':
                    row.append('#' if cnt == 2 or cnt == 3 else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            new.append(row)
        grid = new
    return '\n'.join(''.join(r) for r in grid)
