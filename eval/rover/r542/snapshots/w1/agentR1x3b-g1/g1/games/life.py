def solve(text):
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]

    def step(g):
        out = [['.'] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == '#':
                            n += 1
                if g[r][c] == '#':
                    out[r][c] = '#' if n in (2, 3) else '.'
                else:
                    out[r][c] = '#' if n == 3 else '.'
        return out

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
