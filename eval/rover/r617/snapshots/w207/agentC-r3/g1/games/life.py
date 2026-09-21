"""Conway's Game of Life: evolve k generations on an HxW board."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append([c == "#" for c in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            nb += 1
                if grid[r][c]:
                    nxt[r][c] = nb == 2 or nb == 3
                else:
                    nxt[r][c] = nb == 3
        grid = nxt
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
