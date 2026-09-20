"""Conway's Game of Life: evolve k generations on an HxW grid."""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < h and idx < len(lines):
        row = lines[idx].strip()
        idx += 1
        if row == "":
            continue
        grid.append([ch == "#" for ch in row.ljust(w)[:w]])
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
                nxt[r][c] = (grid[r][c] and n in (2, 3)) or ((not grid[r][c]) and n == 3)
        grid = nxt
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
