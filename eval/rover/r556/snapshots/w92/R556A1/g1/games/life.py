def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = []
    for i in range(H):
        row = lines[1 + i].strip()
        grid.append([c == '#' for c in row])
    for _ in range(k):
        ng = [[False] * W for _ in range(H)]
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
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
