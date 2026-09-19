def solve(text: str) -> str:
    lines = text.split("\n")
    header = lines[0].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    grid = []
    for i in range(h):
        row = lines[1 + i]
        grid.append([c == "#" for c in row[:w]])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt
    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
