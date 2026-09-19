def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [[c == '#' for c in lines[1 + r]] for r in range(H)]
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
                new[r][c] = (grid[r][c] and cnt in (2, 3)) or ((not grid[r][c]) and cnt == 3)
        grid = new
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
