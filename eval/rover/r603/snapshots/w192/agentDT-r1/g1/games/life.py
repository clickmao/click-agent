def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(H):
        row = lines[idx + i] if idx + i < len(lines) else ''
        row = (row + '.' * W)[:W]
        grid.append([c == '#' for c in row])
    for _ in range(k):
        new = [[False] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    new[r][c] = cnt == 2 or cnt == 3
                else:
                    new[r][c] = cnt == 3
        grid = new
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
