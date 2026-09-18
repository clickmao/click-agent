"""Conway's Game of Life: evolve the grid k generations.

Reading: first line ``H W k``; then H lines of W chars over {'.', '#'}.
Rules: simultaneous 8-neighbour update; outside the grid counts as dead.
A live cell survives with 2 or 3 live neighbours, else dies; a dead cell with
exactly 3 live neighbours becomes alive.
"""


def solve(text: str) -> str:
    """Return the grid after k generations, H lines of W chars."""
    lines = text.split("\n")
    idx = 0
    # Skip any leading blank lines defensively (first non-empty line is data).
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1

    rows = []
    for _ in range(h):
        rows.append(lines[idx] if idx < len(lines) else "")
        idx += 1
    grid = [list((row + "." * w)[:w]) for row in rows]

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                alive = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            alive += 1
                if grid[y][x] == "#":
                    nxt[y][x] = "#" if alive in (2, 3) else "."
                else:
                    nxt[y][x] = "#" if alive == 3 else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
