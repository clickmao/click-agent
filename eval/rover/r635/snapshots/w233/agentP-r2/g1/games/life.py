def _parse(text):
    lines = text.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()
    while lines and lines[0].strip() == '':
        lines.pop(0)
    head = lines[0].split()
    h, w, k = int(head[0]), int(head[1]), int(head[2])
    grid = [list(lines[1 + i]) for i in range(h)]
    return h, w, k, grid


def solve(text: str) -> str:
    h, w, k, grid = _parse(text)

    def step(g):
        ng = [['.' for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] == '#':
                            cnt += 1
                if g[y][x] == '#':
                    ng[y][x] = '#' if cnt in (2, 3) else '.'
                else:
                    ng[y][x] = '#' if cnt == 3 else '.'
        return ng

    for _ in range(k):
        grid = step(grid)
    return '\n'.join(''.join(row) for row in grid)
