def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        row = lines[idx].rstrip("\n").rstrip("\r")
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(row[:w])
        idx += 1
    for _ in range(k):
        nxt = []
        for y in range(h):
            rowchars = []
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == "#":
                            cnt += 1
                alive = grid[y][x] == "#"
                if alive:
                    rowchars.append("#" if cnt == 2 or cnt == 3 else ".")
                else:
                    rowchars.append("#" if cnt == 3 else ".")
            nxt.append("".join(rowchars))
        grid = nxt
    return "\n".join(grid)
