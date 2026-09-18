def solve(text: str) -> str:
    data = text.split("\n")
    h, w, k = map(int, data[0].split())
    grid = [[c == '#' for c in data[1 + r]] for r in range(h)]
    for _ in range(k):
        ng = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                if grid[r][c]:
                    ng[r][c] = cnt == 2 or cnt == 3
                else:
                    ng[r][c] = cnt == 3
        grid = ng
    return "\n".join("".join('#' if cell else '.' for cell in row) for row in grid)
