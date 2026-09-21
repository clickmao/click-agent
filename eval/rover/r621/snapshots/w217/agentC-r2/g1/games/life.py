def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    while len(grid) < h:
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        if row == "":
            continue
        row = row.strip()
        if len(row) < w:
            row = row.ljust(w, ".")
        grid.append(list(row[:w]))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            n += 1
                if grid[r][c] == "#":
                    nxt[r][c] = "#" if n in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if n == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
