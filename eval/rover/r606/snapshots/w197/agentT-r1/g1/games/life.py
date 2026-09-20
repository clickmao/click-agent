"""Conway's Game of Life: evolve a grid k generations."""


def step(grid, H, W):
    new = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                        n += 1
            if grid[r][c] == '#':
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        new.append(''.join(row))
    return new


def solve(text):
    lines = text.splitlines()
    H, W, k = (int(x) for x in lines[0].split())
    grid = [lines[1 + i].rstrip('\n') for i in range(H)]
    for _ in range(k):
        grid = step(grid, H, W)
    return '\n'.join(grid)
