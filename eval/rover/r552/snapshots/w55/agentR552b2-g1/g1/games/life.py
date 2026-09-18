def solve(text):
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in lines[1 + r]] for r in range(H)]
    for _ in range(k):
        new = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W:
                            n += grid[rr][cc]
                if grid[r][c]:
                    new[r][c] = 1 if n in (2, 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
