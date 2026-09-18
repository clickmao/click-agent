"""Conway's Game of Life: advance k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(t) for t in lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].strip()
        idx += 1
        grid.append([c == "#" for c in row])

    for _ in range(k):
        new = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            n += 1
                if grid[r][c]:
                    new[r][c] = n == 2 or n == 3
                else:
                    new[r][c] = n == 3
        grid = new

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
