def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = [lines[idx + i] for i in range(h)]
    for _ in range(k):
        new = []
        for r in range(h):
            row = []
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            nb += 1
                alive = grid[r][c] == '#'
                if alive:
                    row.append('#' if nb in (2, 3) else '.')
                else:
                    row.append('#' if nb == 3 else '.')
            new.append(''.join(row))
        grid = new
    return '\n'.join(grid)
