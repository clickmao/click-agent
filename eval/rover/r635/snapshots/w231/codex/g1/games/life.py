"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    h, w, k = (int(x) for x in lines[0].split())
    grid = lines[1:1 + h]
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join(grid)


def _step(grid, h, w):
    new = []
    for r in range(h):
        row = []
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
                row.append("#" if n == 2 or n == 3 else ".")
            else:
                row.append("#" if n == 3 else ".")
        new.append("".join(row))
    return new
