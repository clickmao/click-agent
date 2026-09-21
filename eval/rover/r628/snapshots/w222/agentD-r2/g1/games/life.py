def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
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
                ng[y][x] = n == 3 or (grid[y][x] and n == 2)
        grid = ng
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
