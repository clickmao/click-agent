def _step(g, H, W):
    nxt = []
    for r in range(H):
        row = []
        for c in range(W):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == '#':
                        n += 1
            if g[r][c] == '#':
                row.append('#' if n in (2, 3) else '.')
            else:
                row.append('#' if n == 3 else '.')
        nxt.append(''.join(row))
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    H, W, k = map(int, lines[0].split())
    g = [list(lines[1 + r]) for r in range(H)]
    for _ in range(k):
        g = _step(g, H, W)
    return '\n'.join(''.join(r) for r in g)
