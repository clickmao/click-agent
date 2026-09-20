"""康威生命游戏：H 代演化。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    idx += 1
    grid = []
    for r in range(h):
        row = lines[idx + r] if idx + r < len(lines) else ''
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])

    def step(g):
        out = [[False] * w for _ in range(h)]
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
                    out[y][x] = cnt in (2, 3)
                else:
                    out[y][x] = cnt == 3
        return out

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join('#' if c else '.' for c in row) for row in grid)
