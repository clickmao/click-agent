def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip('\r')
        idx += 1
        row = (row + '.' * w)[:w]
        grid.append(row)

    for _ in range(k):
        new = []
        for r in range(h):
            rowchars = []
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
                    rowchars.append('#' if n in (2, 3) else '.')
                else:
                    rowchars.append('#' if n == 3 else '.')
            new.append(''.join(rowchars))
        grid = new

    return '\n'.join(grid)
