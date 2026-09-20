"""Conway's Game of Life: evolve the grid k generations."""


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ''
        grid.append([1 if c == '#' else 0 for c in row.ljust(w)[:w]])
    for _ in range(k):
        ng = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += grid[rr][cc]
                if grid[r][c]:
                    ng[r][c] = 1 if n in (2, 3) else 0
                else:
                    ng[r][c] = 1 if n == 3 else 0
        grid = ng
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
