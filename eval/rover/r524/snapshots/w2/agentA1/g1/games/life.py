"""康威生命游戏: H 代演化。

入参 text = 完整 stdin 文本; 返回 = 应写出的 stdout 文本(末尾无换行)。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i].rstrip("\r"))[:w] for i in range(h)]

    def step(g):
        out = [["."] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == "#":
                            cnt += 1
                if g[y][x] == "#":
                    out[y][x] = "#" if cnt in (2, 3) else "."
                else:
                    out[y][x] = "#" if cnt == 3 else "."
        return out

    for _ in range(k):
        grid = step(grid)
    return "\n".join("".join(r) for r in grid)
