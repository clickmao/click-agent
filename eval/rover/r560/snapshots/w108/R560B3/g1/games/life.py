def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r][:w]) for r in range(h)]
    for _ in range(k):
        nxt = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            nb += 1
                if grid[r][c] == '#':
                    nxt[r][c] = '#' if nb in (2, 3) else '.'
                else:
                    nxt[r][c] = '#' if nb == 3 else '.'
        grid = nxt
    return '\n'.join(''.join(row) for row in grid)
