def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx] if idx < len(lines) else ""
        row = (row + "." * W)[:W]
        grid.append(list(row))
        idx += 1

    def step(g):
        ng = [["."] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and g[nr][nc] == "#":
                            cnt += 1
                if g[r][c] == "#":
                    ng[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    ng[r][c] = "#" if cnt == 3 else "."
        return ng

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
