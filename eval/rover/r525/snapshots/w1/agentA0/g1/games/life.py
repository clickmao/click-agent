"""康威生命游戏: k 代演化。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r].strip() if idx + r < len(lines) else ""
        row = (row + "." * w)[:w]
        grid.append([c == "#" for c in row])

    def step(g):
        out = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and g[rr][cc]:
                            n += 1
                if g[r][c]:
                    out[r][c] = n == 2 or n == 3
                else:
                    out[r][c] = n == 3
        return out

    for _ in range(k):
        grid = step(grid)

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
