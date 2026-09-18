"""Conway's Game of Life: H x W grid, k generations, simultaneous updates.

Stdin format (per spec):
  first line: H W k
  next H lines: W chars each, '.' (dead) or '#' (alive)

Output: grid after k generations, H lines of W chars.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    h, w, k = map(int, lines[i].split())
    i += 1
    grid = []
    for _ in range(h):
        row = lines[i] if i < len(lines) else ''
        i += 1
        row = row.strip()
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
