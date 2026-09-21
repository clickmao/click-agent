def solve(text):
    lines = text.split("\n")
    head = lines[0].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    grid = [list(lines[1 + i][:w].ljust(w, ".")) for i in range(h)]

    def step(g):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == "#":
                            cnt += 1
                if g[r][c] == "#":
                    nxt[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    nxt[r][c] = "#" if cnt == 3 else "."
        return nxt

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
