"""Conway's Game of Life: evolve H x W grid for k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    # first non-empty line holds H W k
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        # pad/truncate to width w to be robust against trailing spaces
        row = row.replace("\r", "")
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(list(row[:w]))
        idx += 1

    for _ in range(k):
        grid = _step(grid, h, w)

    return "\n".join("".join(r) for r in grid)


def _step(grid, h, w):
    """Simultaneous 8-neighborhood update; out-of-grid cells are dead."""
    new = [["." for _ in range(w)] for _ in range(h)]
    for y in range(h):
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                        n += 1
            if grid[y][x] == "#":
                new[y][x] = "#" if (n == 2 or n == 3) else "."
            else:
                new[y][x] = "#" if n == 3 else "."
    return new
