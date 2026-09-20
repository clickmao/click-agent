def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        idx += 1
        row = row + "." * w
        grid.append([1 if c == "#" else 0 for c in row[:w]])
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    new[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    new[r][c] = 1 if cnt == 3 else 0
        grid = new
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
