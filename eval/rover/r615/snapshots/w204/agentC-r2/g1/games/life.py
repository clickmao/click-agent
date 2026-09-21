def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    while len(grid) < h and idx < len(lines):
        grid.append(lines[idx])
        idx += 1
    grid = [(row + '.' * w)[:w] for row in grid]
    while len(grid) < h:
        grid.append('.' * w)
    for _ in range(k):
        new = []
        for r in range(h):
            out = []
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
                    out.append('#' if n == 2 or n == 3 else '.')
                else:
                    out.append('#' if n == 3 else '.')
            new.append(''.join(out))
        grid = new
    return '\n'.join(grid)
