"""Conway's Game of Life: evolve k generations and return the grid."""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ''
        row = row.rstrip('\r')
        cells = [c == '#' for c in row[:w]]
        while len(cells) < w:
            cells.append(False)
        grid.append(cells)

    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    new[r][c] = n == 2 or n == 3
                else:
                    new[r][c] = n == 3
        grid = new

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
