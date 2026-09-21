def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]

    for _ in range(k):
        new = [['.'] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and grid[yy][xx] == '#':
                            n += 1
                if grid[y][x] == '#':
                    new[y][x] = '#' if n in (2, 3) else '.'
                else:
                    new[y][x] = '#' if n == 3 else '.'
        grid = new

    return '\n'.join(''.join(row) for row in grid)
