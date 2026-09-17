"""Conway's Game of Life: evolve the grid k generations and render it."""


def solve(text: str) -> str:
    """text = full stdin; return the grid after k generations (no trailing newline).

    Rules: simultaneous 8-neighbour update, outside the grid counts as dead.
    Live cell survives with 2 or 3 live neighbours, else dies.
    Dead cell becomes live with exactly 3 live neighbours.
    """
    lines = text.splitlines()
    header = lines[0].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])

    grid = []
    for y in range(h):
        row = lines[1 + y]
        row = (row + "." * w)[:w]
        grid.append([c == "#" for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            n += 1
                if grid[y][x]:
                    nxt[y][x] = n == 2 or n == 3
                else:
                    nxt[y][x] = n == 3
        grid = nxt

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
