"""Game of Life: H x W grid, k simultaneous generations, 8-neighborhood, out-of-bounds dead."""


def _step(grid, h, w):
    nxt = []
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
                row.append("#" if n in (2, 3) else ".")
            else:
                row.append("#" if n == 3 else ".")
        nxt.append("".join(row))
    return nxt


def solve(text):
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = []
    for i in range(1, h + 1):
        row = lines[i].strip() if i < len(lines) else ""
        row = row + "." * (w - len(row))
        grid.append(row[:w])
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join(grid)
