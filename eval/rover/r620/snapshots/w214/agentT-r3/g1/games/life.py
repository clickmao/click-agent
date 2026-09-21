def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    g = [list(lines[1 + r][:w]) for r in range(h)]
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            n += 1
                if g[r][c] == '#':
                    ng[r][c] = '#' if n in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if n == 3 else '.'
        g = ng
    return '\n'.join(''.join(row) for row in g)
