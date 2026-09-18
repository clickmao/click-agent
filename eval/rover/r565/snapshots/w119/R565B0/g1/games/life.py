def solve(text):
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r]
        row = (row + '.' * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if cnt == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
