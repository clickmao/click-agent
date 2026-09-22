"""康威生命游戏：H 行 W 列网格演化 k 代。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list((lines[1 + i] + "." * w)[:w]) for i in range(h)]

    def step(g):
        new = [["."] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == "#":
                            cnt += 1
                if g[r][c] == "#":
                    new[r][c] = "#" if cnt in (2, 3) else "."
                else:
                    new[r][c] = "#" if cnt == 3 else "."
        return new

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(row) for row in grid)
