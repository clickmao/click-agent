"""Conway's Game of Life: evolve k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    first = lines[idx].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = lines[idx + 1: idx + 1 + h]
    grid = []
    for r in range(h):
        row = list(rows[r]) if r < len(rows) else []
        while len(row) < w:
            row.append(".")
        grid.append(row[:w])
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
