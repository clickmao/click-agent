def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for i in range(h):
        row = lines[idx + i] if idx + i < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append(list(row))

    for _ in range(k):
        ng = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            if grid[nr][nc] == "#":
                                cnt += 1
                if grid[r][c] == "#":
                    ng[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    ng[r][c] = "#" if cnt == 3 else "."
        grid = ng

    return "\n".join("".join(row) for row in grid)
