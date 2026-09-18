def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(H):
        row = lines[idx + i]
        grid.append([c == '#' for c in row[:W]])
    out = [row[:] for row in grid]
    for _ in range(k):
        nxt = [[False] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and out[nr][nc]:
                            cnt += 1
                if out[r][c]:
                    nxt[r][c] = cnt in (2, 3)
                else:
                    nxt[r][c] = cnt == 3
        out = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in out)
