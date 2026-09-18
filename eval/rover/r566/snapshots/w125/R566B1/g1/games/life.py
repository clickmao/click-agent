"""Conway's Game of Life: H W k then H lines of W chars of '.' / '#'."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if len(lines) >= 1 and lines[-1] == '':
        lines = lines[:-1]
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(row) for row in lines[1:1 + h]]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            cnt += 1
                if grid[y][x] == '#':
                    new[y][x] = '#' if cnt in (2, 3) else '.'
                else:
                    new[y][x] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
