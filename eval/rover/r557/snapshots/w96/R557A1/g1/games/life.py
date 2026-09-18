"""康威生命游戏：输出第 k 代网格。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    h, w, k = map(int, lines[0].split())
    rows = []
    for i in range(1, h + 1):
        s = lines[i] if i < len(lines) else ""
        s = (s + "." * w)[:w]
        rows.append([c == "#" for c in s])

    def step(grid):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            cnt += 1
                alive = grid[r][c]
                nxt[r][c] = (cnt == 2 or cnt == 3) if alive else (cnt == 3)
        return nxt

    for _ in range(k):
        rows = step(rows)
    return "\n".join("".join("#" if cell else "." for cell in row) for row in rows)
