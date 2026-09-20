"""Conway 生命游戏: 同时更新 k 代, 输出第 k 代网格。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    if idx >= len(lines):
        return ''
    head = lines[idx].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    idx += 1
    grid = []
    while len(grid) < h and idx < len(lines):
        row = lines[idx]
        idx += 1
        if row.strip() == '' and len(row) < w:
            continue
        row = row.rstrip('\r')
        row = (row + '.' * w)[:w]
        grid.append([1 if c == '#' else 0 for c in row])
    while len(grid) < h:
        grid.append([0] * w)

    def step(g):
        ng = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx]:
                            cnt += 1
                if g[y][x]:
                    ng[y][x] = 1 if cnt in (2, 3) else 0
                else:
                    ng[y][x] = 1 if cnt == 3 else 0
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
