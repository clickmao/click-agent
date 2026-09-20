def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    H, W, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + i]] for i in range(H)]

    def step(g):
        ng = [[0] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and g[rr][cc]:
                            n += 1
                if g[r][c]:
                    ng[r][c] = 1 if n in (2, 3) else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)
    out = []
    for r in range(H):
        out.append(''.join('#' if v else '.' for v in grid[r]))
    return '\n'.join(out)
