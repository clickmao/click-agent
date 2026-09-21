"""康威生命游戏: H 代演化。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = (int(x) for x in lines[idx].split())
    grid = []
    for r in range(h):
        idx += 1
        row = lines[idx].strip() if idx < len(lines) else ''
        row = (row + '.' * w)[:w]
        grid.append([c == '#' for c in row])
    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                nxt[r][c] = (grid[r][c] and n in (2, 3)) or ((not grid[r][c]) and n == 3)
        grid = nxt
    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
