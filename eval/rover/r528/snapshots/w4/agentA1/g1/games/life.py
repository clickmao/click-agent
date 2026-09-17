"""康威生命游戏: 演化 k 代。纯函数 solve(text) -> str。"""


def solve(text: str) -> str:
    data = text.split()
    h, w, k = int(data[0]), int(data[1]), int(data[2])
    rows = data[3:3 + h]

    grid = [[1 if c == '#' else 0 for c in row] for row in rows]

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            cnt += grid[nr][nc]
                if grid[r][c]:
                    nxt[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if cnt == 3 else 0
        grid = nxt

    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
