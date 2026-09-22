def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    parts = lines[idx].split()
    h = int(parts[0])
    w = int(parts[1])
    k = int(parts[2])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\r")
        idx += 1
        grid.append([1 if c == "#" else 0 for c in row[:w]])
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += grid[rr][cc]
                if grid[r][c]:
                    new[r][c] = 1 if (n == 2 or n == 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
