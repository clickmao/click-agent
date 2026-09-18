"""康威生命游戏 H 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = map(int, lines[idx].split())
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx].rstrip("\n")
        idx += 1
        chars = list(row)
        grid.append(chars)
    for _ in range(k):
        new_grid = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == "#":
                            alive += 1
                if grid[r][c] == "#":
                    new_grid[r][c] = "#" if alive in (2, 3) else "."
                else:
                    new_grid[r][c] = "#" if alive == 3 else "."
        grid = new_grid
    return "\n".join("".join(row) for row in grid)
