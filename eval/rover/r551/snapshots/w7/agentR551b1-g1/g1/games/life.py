def solve(text):
    lines = text.split('\n')
    if not lines:
        return ''
    first = lines[0].split()
    if len(first) < 3:
        return ''
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[i + 1] if i + 1 < len(lines) else ''
        row = row.ljust(w, '.')
        grid.append(list(row[:w]))
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            nb += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if nb in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if nb == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(r) for r in grid)
