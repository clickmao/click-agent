"""康威生命游戏: 同时更新 k 代后输出网格。

入参为完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行)。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for i in range(h):
        row = lines[1 + i] if 1 + i < len(lines) else ""
        row = row.ljust(w, ".")
        grid.append([1 if ch == "#" else 0 for ch in row[:w]])

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                alive = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            alive += grid[rr][cc]
                if grid[r][c]:
                    nxt[r][c] = 1 if alive in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if alive == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if v else "." for v in row) for row in grid)
