"""Conway's Game of Life: evolve the given grid by k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    if len(first) < 3:
        return ''
    h, w, k = int(first[0]), int(first[1]), int(first[2])

    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ''
        row = row.ljust(w, '.')
        grid.append([1 if c == '#' else 0 for c in row[:w]])

    for _ in range(k):
        new = [[0] * w for _ in range(h)]
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
                    new[r][c] = 1 if n in (2, 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
