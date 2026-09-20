"""康威生命游戏 H 代演化。"""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\n") if idx < len(lines) else ""
        idx += 1
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(list(row[:w]))

    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            cnt += 1
                if grid[r][c] == "#":
                    nxt[r][c] = "#" if cnt == 2 or cnt == 3 else "."
                else:
                    nxt[r][c] = "#" if cnt == 3 else "."
        grid = nxt

    return "\n".join("".join(row) for row in grid)
