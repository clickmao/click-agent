"""Conway's Game of Life: evolve a H x W grid by k generations.

stdin:  first line "H W k"; then H lines of W chars from {'.', '#'}.
stdout: grid after k generations (k=0 => initial grid).

Rules (simultaneous update, outside grid = dead):
  live cell with 2 or 3 live neighbours survives, else dies;
  dead cell with exactly 3 live neighbours becomes alive.
"""


def solve(text: str) -> str:
    """Pure function: full stdin text -> full stdout text (no trailing newline)."""
    lines = text.splitlines()
    if not lines:
        return ""
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[c == "#" for c in lines[1 + r][:w]] for r in range(h)]

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
                alive = grid[r][c]
                nxt[r][c] = (n == 2 or n == 3) if alive else (n == 3)
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
