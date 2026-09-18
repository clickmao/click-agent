"""Conway's Game of Life: k 代同时演化。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    # 去掉首部空行
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    first = lines[idx].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    idx += 1
    grid = []
    for _ in range(h):
        row = lines[idx] if idx < len(lines) else ""
        row = row.rstrip("\r")
        if len(row) < w:
            row = row + "." * (w - len(row))
        grid.append(list(row[:w]))
        idx += 1

    for _ in range(k):
        new = [["."] * w for _ in range(h)]
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
                    new[i][j] = "#" if cnt in (2, 3) else "."
                else:
                    new[i][j] = "#" if cnt == 3 else "."
        grid = new

    return "\n".join("".join(r) for r in grid)
