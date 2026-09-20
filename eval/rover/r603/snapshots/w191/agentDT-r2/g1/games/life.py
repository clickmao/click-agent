def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    while not first:
        lines = lines[1:]
        first = lines[0].split() if lines else []
    h, w, k = map(int, first[:3])
    grid = [list(lines[1 + i]) for i in range(h)]
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
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if n == 2 or n == 3 else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
