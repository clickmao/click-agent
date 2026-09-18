def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split()[:3])
    grid = []
    row = idx + 1
    while len(grid) < h:
        cur = lines[row] if row < len(lines) else ""
        row += 1
        if cur == "" and len(grid) > 0:
            continue
        grid.append(cur[:w].ljust(w, "."))
    for _ in range(k):
        nxt = []
        for r in range(h):
            out = []
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            cnt += 1
                alive = grid[r][c] == "#"
                if alive:
                    out.append("#" if cnt in (2, 3) else ".")
                else:
                    out.append("#" if cnt == 3 else ".")
            nxt.append("".join(out))
        grid = nxt
    return "\n".join(grid)
