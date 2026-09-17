"""Conway's Game of Life -- k generations of synchronous evolution."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [list(row.ljust(w, ".")[:w]) for row in lines[1:1 + h]]

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
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
                alive = grid[y][x] == "#"
                nxt[y][x] = "#" if (n == 3 or (alive and n == 2)) else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
