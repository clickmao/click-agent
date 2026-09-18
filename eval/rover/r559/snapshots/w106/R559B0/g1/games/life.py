import sys


def solve(text: str) -> str:
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    h, w, k = map(int, lines[i].split())
    i += 1
    grid = []
    for _ in range(h):
        grid.append(list(lines[i]))
        i += 1
    for _ in range(k):
        new = [['.' for _ in range(w)] for _ in range(h)]
        for r in range(h):
            for c in range(w):
                cnt = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = r + dr
                        nc = c + dc
                        if 0 <= nr < h and 0 <= nc < w and grid[nr][nc] == '#':
                            cnt += 1
                if grid[r][c] == '#':
                    new[r][c] = '#' if cnt in (2, 3) else '.'
                else:
                    new[r][c] = '#' if cnt == 3 else '.'
        grid = new
    return '\n'.join(''.join(row) for row in grid)
