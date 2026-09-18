def solve(text):
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].split()
    if len(first) < 3:
        return ""
    h = int(first[0])
    w = int(first[1])
    k = int(first[2])
    grid = []
    for i in range(1, 1 + h):
        row = lines[i] if i < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append([ch == "#" for ch in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        grid = nxt
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
