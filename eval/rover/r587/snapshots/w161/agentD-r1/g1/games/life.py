"""Conway's Game of Life: k-step evolution on a finite grid with dead borders."""


def solve(text: str) -> str:
    lines = text.split('\n')
    head = lines[0].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == '#':
                            n += 1
                if grid[y][x] == '#':
                    nxt[y][x] = '#' if n in (2, 3) else '.'
                else:
                    nxt[y][x] = '#' if n == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
