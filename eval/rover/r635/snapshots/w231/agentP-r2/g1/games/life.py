"""Conway's Game of Life: k generations of simultaneous 8-neighbour updates.

Input text:
    line 1: H W k
    next H lines: W chars from {'.', '#'}
Output text: H lines of W chars, the grid after k generations.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    head = lines[0].split() if lines else []
    if len(head) < 3:
        return ''
    h, w, k = (int(x) for x in head[:3])
    grid = []
    for r in range(h):
        row = lines[1 + r] if 1 + r < len(lines) else ''
        row = row.ljust(w, '.')
        grid.append([c == '#' for c in row[:w]])
    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    new[r][c] = n in (2, 3)
                else:
                    new[r][c] = n == 3
        grid = new
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
