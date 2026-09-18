def solve(text):
    lines = text.split("\n")
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + r]) for r in range(H)]
    for _ in range(k):
        nxt = []
        for r in range(H):
            row = []
            for c in range(W):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    row.append('#' if cnt == 2 or cnt == 3 else '.')
                else:
                    row.append('#' if cnt == 3 else '.')
            nxt.append(row)
        grid = nxt
    return "\n".join("".join(row) for row in grid)
