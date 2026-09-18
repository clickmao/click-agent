"""康威生命游戏：H 代演化。

solve(text) 接收完整 stdin 文本，返回应写出的 stdout 文本（末尾无换行）。
首行 H W k；随后 H 行每行 W 个字符（'.' 死 / '#' 活）。
"""


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    rows = []
    while len(rows) < h:
        if idx >= len(lines):
            break
        line = lines[idx].rstrip('\r')
        idx += 1
        if line == '':
            continue
        rows.append(line + '.' * (w - len(line)))
    grid = [[1 if ch == '#' else 0 for ch in row[:w]] for row in rows]
    for _ in range(k):
        new = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and grid[ny][nx]:
                            cnt += 1
                if grid[y][x]:
                    new[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    new[y][x] = 1 if cnt == 3 else 0
        grid = new
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
