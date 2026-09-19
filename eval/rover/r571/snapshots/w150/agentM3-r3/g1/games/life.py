def solve(text):
    lines = text.split("\n")
    first = lines[0].split()
    H, W, k = int(first[0]), int(first[1]), int(first[2])
    grid = [list(lines[1 + i][:W]) for i in range(H)]
    for _ in range(k):
        new = [["."] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == "#":
                            cnt += 1
                if grid[r][c] == "#":
                    new[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    new[r][c] = "#" if cnt == 3 else "."
        grid = new
    return "\n".join("".join(row) for row in grid)
