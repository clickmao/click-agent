"""Conway's Game of Life: H 行 W 列网格演化 k 代。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    h, w, k = (int(x) for x in lines[0].split()[:3])
    rows = lines[1:1 + h]
    grid = [[1 if ch == "#" else 0 for ch in (row.ljust(w, ".")[:w])] for row in rows]
    while len(grid) < h:
        grid.append([0] * w)

    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                nb = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w:
                            nb += grid[ni][nj]
                if grid[i][j]:
                    new[i][j] = 1 if (nb == 2 or nb == 3) else 0
                else:
                    new[i][j] = 1 if nb == 3 else 0
        grid = new

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
