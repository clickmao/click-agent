def step(grid, h, w):
    new = []
    for r in range(h):
        row = []
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            if alive:
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        new.append(row)
    return new


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]
    for _ in range(k):
        grid = step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
