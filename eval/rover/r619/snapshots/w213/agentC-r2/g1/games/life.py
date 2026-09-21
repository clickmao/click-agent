"""Conway's Game of Life: advance k generations on an H x W grid."""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\r") if idx < len(lines) else ""
        idx += 1
        row = (row + "." * w)[:w]
        grid.append(list(row))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            alive += 1
                if grid[r][c] == "#":
                    nxt[r][c] = "#" if alive in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if alive == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
