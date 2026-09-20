"""Conway's Game of Life: evolve the grid by k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    h, w, k = map(int, lines[0].split())
    grid = []
    for r in range(h):
        row = lines[1 + r] if 1 + r < len(lines) else ""
        row = row.ljust(w, ".")
        grid.append(list(row[:w]))

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
                    new[r][c] = "#" if n in (2, 3) else "."
                else:
                    new[r][c] = "#" if n == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
