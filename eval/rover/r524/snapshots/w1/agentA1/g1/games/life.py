"""Game `life`: Conway's Game of Life, `k` generations.

Input : first line "H W k" (1<=H,W<=20, 0<=k<=20); then H lines of W chars,
        each '.' (dead) or '#' (alive).
Output: grid after k generations (k=0 -> initial), H lines of W chars.

Rules: simultaneous 8-neighbourhood update; everything outside the grid is a
dead cell. A live cell survives iff its neighbour count is 2 or 3, otherwise it
dies. A dead cell becomes alive iff it has exactly 3 live neighbours.
"""


def _step(grid, h, w):
    """Return the next generation of `grid` (list of lists of bool)."""
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
            nxt[r][c] = (n == 3) if not grid[r][c] else (n == 2 or n == 3)
    return nxt


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [[ch == '#' for ch in lines[1 + r]] for r in range(h)]

    for _ in range(k):
        grid = _step(grid, h, w)

    return "\n".join("".join('#' if cell else '.' for cell in row) for row in grid)
