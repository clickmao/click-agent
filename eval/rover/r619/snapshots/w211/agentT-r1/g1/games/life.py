"""康威生命游戏: H 代演化。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    h, w, k = map(int, lines[idx].split()[:3])
    idx += 1
    grid = []
    for i in range(h):
        row = ''
        if idx + i < len(lines):
            row = lines[idx + i]
        row = row.replace('\r', '')
        row = row.ljust(w, '.')[:w]
        grid.append([c == '#' for c in row])

    def step():
        nxt = [[False] * w for _ in range(h)]
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
                    nxt[r][c] = cnt == 2 or cnt == 3
                else:
                    nxt[r][c] = cnt == 3
        return nxt

    for _ in range(k):
        grid = step()

    return '\n'.join(''.join('#' if v else '.' for v in row) for row in grid)
