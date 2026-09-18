def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    idx = 0
    h = int(tokens[idx]); idx += 1
    w = int(tokens[idx]); idx += 1
    k = int(tokens[idx]); idx += 1
    grid = [[0] * w for _ in range(h)]
    for r in range(h):
        row = tokens[idx]; idx += 1
        for c in range(w):
            if row[c] == '#':
                grid[r][c] = 1

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            alive += grid[rr][cc]
                if grid[r][c]:
                    nxt[r][c] = 1 if alive in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if alive == 3 else 0
        grid = nxt

    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
