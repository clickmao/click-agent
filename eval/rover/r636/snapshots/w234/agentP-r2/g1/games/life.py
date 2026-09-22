def solve(text):
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]
    for _ in range(k):
        ng = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    ng[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if cnt == 3 else '.'
        grid = ng
    return '\n'.join(''.join(row) for row in grid)
