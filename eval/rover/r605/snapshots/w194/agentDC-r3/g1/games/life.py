"""Conway's Game of Life: evolve k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append([c == "#" for c in row])

    def step(g):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                            n += 1
                if g[r][c]:
                    ng[r][c] = n in (2, 3)
                else:
                    ng[r][c] = n == 3
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
