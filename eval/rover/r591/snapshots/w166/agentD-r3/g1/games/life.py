def solve(text):
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(H):
        row = lines[idx + i].rstrip('\n')
        row = row.ljust(W, '.')
        grid.append(list(row[:W]))
    for _ in range(k):
        nxt = [['.' for _ in range(W)] for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            n += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if (n == 2 or n == 3) else '.'
                else:
                    nxt[r][c] = '#' if n == 3 else '.'
        grid = nxt
    out = ['\n'.join(''.join(row) for row in grid)]
    return out[0]
