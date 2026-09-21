def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    H, W, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(H):
        grid.append(list(lines[idx + r]))
    for _ in range(k):
        new = [["."] * W for _ in range(H)]
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
        grid = new
    return "\n".join("".join(row) for row in grid)
