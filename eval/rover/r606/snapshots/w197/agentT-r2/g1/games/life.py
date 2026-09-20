def solve(text: str) -> str:
    lines = text.split()
    h, w, k = int(lines[0]), int(lines[1]), int(lines[2])
    grid = [list(lines[3 + i]) for i in range(h)]
    for _ in range(k):
        new = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if n in (2, 3) else '.'
                else:
                    new[r][c] = '#' if n == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
