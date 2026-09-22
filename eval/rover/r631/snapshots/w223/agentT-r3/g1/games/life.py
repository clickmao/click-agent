def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    rows = []
    j = idx + 1
    while len(rows) < H:
        if j < len(lines) and lines[j] != '':
            rows.append(lines[j])
        j += 1
        if j > len(lines):
            break
    grid = [[1 if c == '#' else 0 for c in r.ljust(W, '.')[:W]] for r in rows]
    for _ in range(k):
        new = [[0] * W for _ in range(H)]
        for i in range(H):
            for j2 in range(W):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j2 + dj
                        if 0 <= ni < H and 0 <= nj < W and grid[ni][nj]:
                            cnt += 1
                if grid[i][j2]:
                    new[i][j2] = 1 if cnt in (2, 3) else 0
                else:
                    new[i][j2] = 1 if cnt == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
