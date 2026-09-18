"""Conway's Game of Life: evolve H x W grid for k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i]
        grid.append(list(row[:w].ljust(w, ".")))

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
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
                    nxt[r][c] = "#" if n in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if n == 3 else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
