def solve(text: str) -> str:
    lines = text.split('\n')
    H, W, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in lines[1 + i]] for i in range(H)]

    def step(g):
        out = [[0] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                nb = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            nb += g[ny][nx]
                if g[y][x]:
                    out[y][x] = 1 if nb in (2, 3) else 0
                else:
                    out[y][x] = 1 if nb == 3 else 0
        return out

    for _ in range(k):
        grid = step(grid)

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
