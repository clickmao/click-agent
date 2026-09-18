"""Conway's Game of Life on a bounded grid with dead borders."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    header = lines[0].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for y in range(h):
            row = grid[y]
            for x in range(w):
                live = 0
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= h:
                        continue
                    nrow = grid[ny]
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        if nx < 0 or nx >= w:
                            continue
                        live += nrow[nx]
                if row[x]:
                    new[y][x] = 1 if live in (2, 3) else 0
                else:
                    new[y][x] = 1 if live == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
