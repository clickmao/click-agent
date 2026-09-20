def solve(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in line] for line in lines[1:1 + h]]
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    ng[r][c] = 1 if n == 2 or n == 3 else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if x else '.' for x in row) for row in grid)
