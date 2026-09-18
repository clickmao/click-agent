def solve(text):
    lines = text.split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r][:W]) for r in range(H)]
    for _ in range(k):
        new = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            nb += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if nb in (2, 3) else '.'
                else:
                    new[r][c] = '#' if nb == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
