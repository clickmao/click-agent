"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while not lines[idx].strip():
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r]
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
                    new[r][c] = n == 2 or n == 3
                else:
                    new[r][c] = n == 3
        grid = new

    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
