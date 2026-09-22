"""Conway's Game of Life: evolve a bounded grid for k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    h, w, k = map(int, lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ""
        row = row[:w]
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(list(row))
    for _ in range(k):
        nxt = [["."] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj] == "#":
                            cnt += 1
                if grid[i][j] == "#":
                    nxt[i][j] = "#" if cnt in (2, 3) else "."
                else:
                    nxt[i][j] = "#" if cnt == 3 else "."
        grid = nxt
    return "\n".join("".join(row) for row in grid)
