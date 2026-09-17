"""Conway's Game of Life: k generations, simultaneous update, 8-neighborhood,
out-of-grid cells treated as dead. Pure function solve(text) -> str (no trailing newline).
"""


def _parse(text):
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + i].rstrip("\n")) for i in range(h)]
    return h, w, k, grid


def _step(h, w, grid):
    out = [["." for _ in range(w)] for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        n += 1
            alive = grid[r][c] == "#"
            if alive:
                out[r][c] = "#" if (n == 2 or n == 3) else "."
            else:
                out[r][c] = "#" if n == 3 else "."
    return out


def solve(text: str) -> str:
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(h, w, grid)
    return "\n".join("".join(row) for row in grid)
