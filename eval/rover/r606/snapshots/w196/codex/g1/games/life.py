def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = map(int, lines[0].split())
    grid = [[1 if c == '#' else 0 for c in lines[1 + r]] for r in range(h)]
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            n += grid[nr][nc]
                if grid[r][c]:
                    new[r][c] = 1 if n in (2, 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new
    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
