def solve(text: str) -> str:
    data = text.split()
    if not data:
        return ""
    h, w, k = (int(x) for x in data[:3])
    lines = data[3:3 + h]
    grid = [[1 if c == '#' else 0 for c in row] for row in lines]
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
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            n += 1
                if grid[r][c]:
                    new[r][c] = 1 if n in (2, 3) else 0
                else:
                    new[r][c] = 1 if n == 3 else 0
        grid = new
    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
