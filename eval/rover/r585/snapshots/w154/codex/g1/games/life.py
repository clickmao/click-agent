"""Conway's Game of Life: evolve a grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    header = lines[idx].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    idx += 1
    grid = [list(lines[idx + i]) for i in range(h)]

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
