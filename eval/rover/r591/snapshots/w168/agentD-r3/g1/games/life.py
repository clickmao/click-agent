def solve(text: str) -> str:
    lines = text.splitlines()
    H, W, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(H)]
    for _ in range(k):
        nxt = [
            [
                "#"
                if sum(
                    1
                    for dr in (-1, 0, 1)
                    for dc in (-1, 0, 1)
                    if (dr or dc)
                    and 0 <= r + dr < H
                    and 0 <= c + dc < W
                    and grid[r + dr][c + dc] == "#"
                )
                in ((3,) if grid[r][c] == "." else (2, 3))
                else "."
                for c in range(W)
            ]
            for r in range(H)
        ]
        grid = nxt
    return "\n".join("".join(row) for row in grid)
