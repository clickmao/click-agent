def solve(text: str) -> str:
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    H, W, k = map(int, lines[0].split())
    grid = [list(lines[1 + r]) for r in range(H)]
    for _ in range(k):
        ng = [["."] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] == "#":
                            n += 1
                if grid[r][c] == "#":
                    ng[r][c] = "#" if n == 2 or n == 3 else "."
                else:
                    ng[r][c] = "#" if n == 3 else "."
        grid = ng
    return "\n".join("".join(row) for row in grid)
