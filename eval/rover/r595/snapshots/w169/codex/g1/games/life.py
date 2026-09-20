"""Conway's Game of Life: evolve a grid k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    header = lines[idx].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    idx += 1

    grid = []
    for row in range(h):
        line = lines[idx + row].strip() if idx + row < len(lines) else ""
        line = (line + "." * w)[:w]
        grid.append([c == "#" for c in line])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                nxt[r][c] = n == 3 or (grid[r][c] and n == 2)
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
