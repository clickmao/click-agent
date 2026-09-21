def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r].rstrip('\n').rstrip('\r')
        row = row.ljust(w, '.')
        grid.append([1 if c == '#' else 0 for c in row[:w]])
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            nb += grid[rr][cc]
                if grid[r][c]:
                    nxt[r][c] = 1 if nb in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if nb == 3 else 0
        grid = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
