"""康威生命游戏：按 8 邻域同步演化 k 代。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[0] * w for _ in range(h)]
    for i in range(h):
        row = lines[1 + i]
        for j in range(w):
            if j < len(row) and row[j] == "#":
                grid[i][j] = 1
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
                        if 0 <= ni < h and 0 <= nj < w and grid[ni][nj]:
                            cnt += 1
                if grid[i][j]:
                    nxt[i][j] = 1 if cnt == 2 or cnt == 3 else 0
                else:
                    nxt[i][j] = 1 if cnt == 3 else 0
        grid = nxt
    return "\n".join("".join("#" if c else "." for c in row) for row in grid)
