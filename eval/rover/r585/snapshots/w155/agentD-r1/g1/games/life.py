def solve(text):
    lines = text.split('\n')
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]
    for _ in range(k):
        new = []
        for r in range(h):
            row = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            new.append(row)
        grid = new
    return '\n'.join(''.join(row) for row in grid)
