def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    h, w, k = map(int, lines[i].split())
    i += 1
    grid = [list((lines[i + r] if i + r < len(lines) else '').ljust(w, '.')[:w]) for r in range(h)]
    for _ in range(k):
        ng = [['.'] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    ng[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[r][c] = '#' if cnt == 3 else '.'
        grid = ng
    return '\n'.join(''.join(row) for row in grid)
