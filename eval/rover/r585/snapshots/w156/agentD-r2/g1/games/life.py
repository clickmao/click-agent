"""Conway's Game of Life: H W k plus an initial H-by-W grid of '.' and '#'.

solve(text) returns the grid after k simultaneous generations. Cells outside
  the grid are always dead. A live cell survives with 2 or 3 live neighbours; a
dead cell becomes live with exactly 3 live neighbours. The returned text has H
lines of W characters joined by '\n' and no trailing newline.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return ""
    header = lines[0].split()
    if not header:
        return ""
    h, w, k = (int(x) for x in header[:3])
    rows = [line.ljust(w, ".")[:w] for line in lines[1:1 + h]]
    while len(rows) < h:
        rows.append("." * w)

    grid = [[1 if ch == "#" else 0 for ch in row] for row in rows]

    def neighbours(g, r, c):
        total = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and g[nr][nc]:
                    total += 1
        return total

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = neighbours(grid, r, c)
                if grid[r][c]:
                    nxt[r][c] = 1 if n in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if n == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
