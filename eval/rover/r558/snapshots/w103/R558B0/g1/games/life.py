"""Game: Conway's Life, advance k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]

    dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy, dx in dirs:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                        n += 1
                if grid[y][x] == '#':
                    nxt[y][x] = '#' if n in (2, 3) else '.'
                else:
                    nxt[y][x] = '#' if n == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
