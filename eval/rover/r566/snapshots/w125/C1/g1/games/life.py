def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(H):
        row = lines[idx + r].strip()
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
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    new[r][c] = cnt == 2 or cnt == 3
                else:
                    new[r][c] = cnt == 3
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
