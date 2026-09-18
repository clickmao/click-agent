def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < H and idx < len(lines):
        row = lines[idx].rstrip('\r')
        idx += 1
        if row == '' and len(grid) == 0:
            continue
        grid.append(row)
    for _ in range(k):
        ng = []
        for r in range(H):
            row = []
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            ng.append(''.join(row))
        grid = ng
    return '\n'.join(grid)
