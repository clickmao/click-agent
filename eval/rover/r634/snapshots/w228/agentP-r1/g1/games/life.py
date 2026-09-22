"""Conway's Game of Life: evolve the given grid k generations."""


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r][:w]] for r in range(h)]
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
                        if 0 <= rr < h and 0 <= cc < w:
                            n += grid[rr][cc]
                if grid[r][c]:
                    new[r][c] = 1 if n in (2, 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if cell else '.' for cell in row) for row in grid)
