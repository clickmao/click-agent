def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(h):
        row = lines[idx + 1 + r]
        grid.append([c == '#' for c in row[:w]])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                live = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            live += 1
                if grid[r][c]:
                    nxt[r][c] = live == 2 or live == 3
                else:
                    nxt[r][c] = live == 3
        grid = nxt
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
