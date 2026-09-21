"""Conway's Game of Life."""


def _parse(text):
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r].strip()) for r in range(h)]
    return h, w, k, grid


def _step(grid, h, w):
    nxt = [["."] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            live = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                        live += 1
            if grid[r][c] == "#":
                nxt[r][c] = "#" if live in (2, 3) else "."
            else:
                nxt[r][c] = "#" if live == 3 else "."
    return nxt


def solve(text: str) -> str:
    h, w, k, grid = _parse(text)
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join(row) for row in grid)
