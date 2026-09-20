def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx]
        idx += 1
        grid.append([1 if c == '#' else 0 for c in row])
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            nb += 1
                if grid[r][c]:
                    ng[r][c] = 1 if nb == 2 or nb == 3 else 0
                else:
                    ng[r][c] = 1 if nb == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
