"""康威生命游戏 k 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    h, w, k = (int(x) for x in lines[i].split())
    i += 1
    grid = []
    for r in range(h):
        row = lines[i + r] if i + r < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append(list(row))

    for _ in range(k):
        ng = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            n += 1
                if grid[r][c] == "#":
                    ng[r][c] = "#" if n in (2, 3) else "."
                else:
                    ng[r][c] = "#" if n == 3 else "."
        grid = ng

    return "\n".join("".join(row) for row in grid)
