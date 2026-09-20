def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[ch for ch in lines[1 + r][:w]] for r in range(h)]
    for _ in range(k):
        ng = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            n += 1
                if grid[r][c] == "#":
                    if n == 2 or n == 3:
                        ng[r][c] = "#"
                elif n == 3:
                    ng[r][c] = "#"
        grid = ng
    return "\n".join("".join(row) for row in grid)
