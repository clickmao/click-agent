"""康威生命游戏: 计算 k 代演化后的网格。"""


def solve(text: str) -> str:
    """输入完整 stdin 文本, 返回应写出的 stdout 文本(末尾不带换行)。"""
    lines = text.splitlines()
    if not lines:
        return ""
    h, w, k = (int(x) for x in lines[0].split())
    grid = []
    for i in range(h):
        row = lines[1 + i].strip()
        grid.append([1 if c == '#' else 0 for c in row.ljust(w, '.')[:w]])

    def step(g):
        ng = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                nb = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx]:
                            nb += 1
                if g[y][x]:
                    ng[y][x] = 1 if nb in (2, 3) else 0
                else:
                    ng[y][x] = 1 if nb == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)

    return "\n".join("".join('#' if c else '.' for c in row) for row in grid)
