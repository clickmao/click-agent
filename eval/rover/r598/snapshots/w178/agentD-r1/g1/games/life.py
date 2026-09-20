def solve(text: str) -> str:
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    g = [list(lines[1 + r]) for r in range(H)]

    def step(g):
        ng = []
        for r in range(H):
            row = []
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
                    row.append('#' if n in (2, 3) else '.')
                else:
                    row.append('#' if n == 3 else '.')
            ng.append(row)
        return ng

    for _ in range(k):
        g = step(g)
    return '\n'.join(''.join(row) for row in g)
