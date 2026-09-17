def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(H):
        row = lines[idx].rstrip("\r\n")
        idx += 1
        if len(row) < W:
            row = row + "." * (W - len(row))
        grid.append(row[:W])

    for _ in range(k):
        new = [["." for _ in range(W)] for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W and grid[nr][nc] == "#":
                            cnt += 1
                if grid[r][c] == "#":
                    new[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    new[r][c] = "#" if cnt == 3 else "."
        grid = ["".join(row) for row in new]

    return "\n".join(grid)
