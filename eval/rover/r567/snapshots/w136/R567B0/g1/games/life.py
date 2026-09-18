def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx].strip()
        idx += 1
        cells = []
        for c in range(w):
            cells.append(1 if (c < len(row) and row[c] == '#') else 0)
        grid.append(cells)

    def step(g):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            cnt += g[nr][nc]
                if g[r][c] == 1:
                    ng[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    ng[r][c] = 1 if cnt == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
