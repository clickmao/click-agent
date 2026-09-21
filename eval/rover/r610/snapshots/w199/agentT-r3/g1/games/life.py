"""康威生命游戏：k 代同时更新，网格外视为死格。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0] == "":
        lines = lines[1:]
    header = lines[0].split()
    h, w, k = int(header[0]), int(header[1]), int(header[2])
    grid = [list(lines[1 + i]) for i in range(h)]

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == "#":
                            n += 1
                if grid[r][c] == "#":
                    new[r][c] = "#" if n in (2, 3) else "."
                else:
                    new[r][c] = "#" if n == 3 else "."
        grid = new

    return "\n".join("".join(row) for row in grid)
