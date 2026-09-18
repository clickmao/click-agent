"""Conway's Game of Life: evolve the grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + r]) for r in range(h)]

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            alive += 1
                if grid[r][c] == "#":
                    nxt[r][c] = "#" if alive in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if alive == 3 else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
