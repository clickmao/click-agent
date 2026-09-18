"""Conway's Game of Life."""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [list(lines[1 + r].rstrip()) for r in range(h)]

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nbrs = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            nbrs += 1
                if grid[r][c] == "#":
                    new[r][c] = "#" if nbrs in (2, 3) else "."
                else:
                    new[r][c] = "#" if nbrs == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
