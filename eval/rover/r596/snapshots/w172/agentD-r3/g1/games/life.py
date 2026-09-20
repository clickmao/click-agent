"""Conway's Game of Life: H x W grid, k generations."""


def _neighbors(g, r, c, h, w):
    cnt = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                cnt += 1
    return cnt


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip() if idx < len(lines) else ''
        idx += 1
        if len(row) < w:
            row = row + '.' * (w - len(row))
        grid.append(row[:w])
    cur = grid
    for _ in range(k):
        nxt = []
        for r in range(h):
            row = []
            for c in range(w):
                n = _neighbors(cur, r, c, h, w)
                if cur[r][c] == '#':
                    row.append('#' if n in (2, 3) else '.')
                else:
                    row.append('#' if n == 3 else '.')
            nxt.append(''.join(row))
        cur = nxt
    return '\n'.join(cur)
