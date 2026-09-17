"""康威生命游戏：输出第 k 代之后的网格。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    # 跳过可能的空首行之外，直接按行解析；首行为头部
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(h):
        row = lines[idx + 1 + r] if idx + 1 + r < len(lines) else ""
        # 仅取前 w 个字符（防御行尾多余空白）
        row = row[:w]
        grid.append([1 if ch == '#' else 0 for ch in row])

    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc]:
                            cnt += 1
                if grid[r][c]:
                    new[r][c] = 1 if cnt in (2, 3) else 0
                else:
                    new[r][c] = 1 if cnt == 3 else 0
        grid = new

    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
