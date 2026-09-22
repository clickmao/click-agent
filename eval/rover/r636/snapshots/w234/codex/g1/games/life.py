"""Conway's Game of Life evolution."""


def _step(grid, h, w):
    out = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr = r + dr
                    cc = c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                        n += 1
            if grid[r][c]:
                out[r][c] = n == 2 or n == 3
            else:
                out[r][c] = n == 3
    return out


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r].rstrip("\r")
        grid.append([ch == "#" for ch in row[:w]])
    for _ in range(k):
        grid = _step(grid, h, w)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
