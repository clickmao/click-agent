def solve(text: str) -> str:
    lines = text.split(chr(10))
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i]) for i in range(h)]

    def step(g):
        out = []
        for r in range(h):
            row = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == '#':
                            cnt += 1
                if g[r][c] == '#':
                    row.append('#' if cnt in (2, 3) else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            out.append(row)
        return out

    for _ in range(k):
        grid = step(grid)
    return chr(10).join(''.join(row) for row in grid)
