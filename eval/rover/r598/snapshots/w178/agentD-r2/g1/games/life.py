def solve(text: str) -> str:
    lines = text.splitlines()
    ptr = 0
    while ptr < len(lines) and lines[ptr].strip() == "":
        ptr += 1
    h, w, k = map(int, lines[ptr].split())
    ptr += 1
    grid = []
    for _ in range(h):
        grid.append(list(lines[ptr].strip()))
        ptr += 1
    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                if grid[r][c] == "#":
                    new[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    new[r][c] = "#" if cnt == 3 else "."
        grid = new
    return "\n".join("".join(row) for row in grid)
