"""Conway's Game of Life: evolve H x W grid k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i][:w]) for i in range(h)]
    # pad input rows to width w with dead cells
    for i in range(h):
        if len(grid[i]) < w:
            grid[i] = grid[i] + ['.'] * (w - len(grid[i]))
    cur = grid
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and cur[rr][cc] == '#':
                            n += 1
                alive = cur[r][c] == '#'
                if alive:
                    nxt[r][c] = '#' if (n == 2 or n == 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        cur = nxt
    return '\n'.join(''.join(row) for row in cur)
