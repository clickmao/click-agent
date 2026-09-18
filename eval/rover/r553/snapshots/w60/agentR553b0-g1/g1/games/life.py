"""Conway's Game of Life: k-step evolution of an H x W grid."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split()[:3])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        row = (row + "." * w)[:w]
        grid.append([c == "#" for c in row])

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
                if grid[r][c]:
                    nxt[r][c] = n in (2, 3)
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
