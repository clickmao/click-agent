"""Conway's Game of Life: evolve the grid by k generations."""


def solve(text: str) -> str:
    """Read 'H W k' then H rows of W chars ('.'/'#'); return generation k.

    Rules: simultaneous update, 8-neighbourhood, outside of grid = dead.
    Live cell survives with 2 or 3 live neighbours; dead cell with exactly
    3 live neighbours becomes live.
    """
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
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
                if grid[r][c] == "#":
                    new[r][c] = "#" if n == 2 or n == 3 else "."
                else:
                    new[r][c] = "#" if n == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
