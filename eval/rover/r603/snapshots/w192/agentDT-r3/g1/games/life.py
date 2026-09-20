def solve(text):
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:W]) for i in range(H)]

    def alive(cells, r, c):
        if r < 0 or r >= H or c < 0 or c >= W:
            return 0
        return 1 if cells[r][c] == '#' else 0

    for _ in range(k):
        nxt = [['.' for _ in range(W)] for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        n += alive(grid, r + dr, c + dc)
                if grid[r][c] == '#':
                    if n == 2 or n == 3:
                        nxt[r][c] = '#'
                else:
                    if n == 3:
                        nxt[r][c] = '#'
        grid = nxt

    return '\n'.join(''.join(row) for row in grid)
