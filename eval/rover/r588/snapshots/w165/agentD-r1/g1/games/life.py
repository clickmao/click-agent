"""Conway's Game of Life: H W k then H rows of '.'/'#'; output grid after k generations."""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for r in range(h):
        row = lines[1 + r] if 1 + r < len(lines) else ""
        cells = [1 if row[c] == "#" else 0 for c in range(w)]
        grid.append(cells)

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for i in range(h):
            for j in range(w):
                cnt = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < h and 0 <= nj < w:
                            cnt += grid[ni][nj]
                if grid[i][j]:
                    nxt[i][j] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[i][j] = 1 if cnt == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
