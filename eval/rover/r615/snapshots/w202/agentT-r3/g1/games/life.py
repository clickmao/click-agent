def solve(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].split()
    if len(first) < 3:
        first = text.split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    rows = lines[1:1 + h]
    if len(rows) < h:
        rows = text.split()[3:3 + h]
    grid = [list(rows[i]) for i in range(h)]
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
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
                    nxt[r][c] = "#" if cnt == 2 or cnt == 3 else "."
                else:
                    nxt[r][c] = "#" if cnt == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
