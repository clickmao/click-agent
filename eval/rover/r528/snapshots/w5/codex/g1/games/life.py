def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i][:W]) for i in range(H)]

    def step(g):
        ng = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    ng[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if cnt == 3 else '.'
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
